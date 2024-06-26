#!/usr/bin/env python3

# Basic script to finetune causal LM using HF Trainer.

import random
import sys
import json

from argparse import ArgumentParser

from datasets import load_dataset
from transformers import (
    AutoTokenizer,
    AutoModelForCausalLM,
    DataCollatorForLanguageModeling,
    TrainingArguments,
    Trainer,
)


def argparser():
    ap = ArgumentParser()
    ap.add_argument('--key', default='text')
    ap.add_argument('--verbose', action='store_true')
    ap.add_argument('--max-length', type=int, default=1024)
    ap.add_argument('--model')
    ap.add_argument('--train_data')
    ap.add_argument('--eval_data')
    return ap

def prepper(data):
    data = data.train_test_split(test_size=0.2)
    template = "<|user|>Käännä suomeksi: {} <|assistant|>"
    formatted_data = {}

    train = []
    for idx, entry in enumerate(data["train"]["translation"]):
        formatted_en = template.format(entry["en"])
        response = entry["fi"]
        final = f"{formatted_en}{response}"
        train.append(final)
    formatted_data["train"] = train

    test = []
    for idx, entry in enumerate(data["test"]["translation"]):
        formatted_en = template.format(entry["en"])
        response = entry["fi"]
        final = f"{formatted_en}{response}"
        test.append(final)
    formatted_data["test"] = test

    return formatted_data

def main(argv):
    args = argparser().parse_args(argv[1:])

    #data = load_dataset('json', data_files={
    #    'train': args.train_data,
    #    'eval': args.eval_data,
    #})
    train_args = TrainingArguments(
        output_dir='train_output',
        evaluation_strategy='steps',
        save_strategy='no',
        eval_steps=100,
        num_train_epochs=10,
        bf16=True,
        bf16_full_eval=True
    )
    #print(f"Args {train_args}")
    ds = load_dataset("Helsinki-NLP/europarl", "en-fi", split="train")
    ds = ds.shuffle(random.seed(5834))  # Shuffle dataset
    data = prepper(data=ds.select(range(10000)))
    tokenizer = AutoTokenizer.from_pretrained(args.model)
    def tokenize(example):
        return tokenizer(
            example,
            max_length=args.max_length,
            truncation=True,
        )
    data_train_tokenized = list(map(tokenize, data["train"]))
    data_test_tokenized = list(map(tokenize, data["test"]))
    model = AutoModelForCausalLM.from_pretrained(
        args.model,
        torch_dtype='auto',
    )


    collator = DataCollatorForLanguageModeling(
        tokenizer=tokenizer,
        return_tensors='pt',
        mlm=False,
    )



    trainer = Trainer(
        args=train_args,
        model=model,
        tokenizer=tokenizer,
        data_collator=collator,
        train_dataset=data_train_tokenized,
        eval_dataset=data_test_tokenized
    )

    result = trainer.evaluate()
    print(f'loss before training: {result["eval_loss"]:.2f}')

    trainer.train()

    result = trainer.evaluate()
    print(f'loss after training: {result["eval_loss"]:.2f}')


if __name__ == '__main__':
    sys.exit(main(sys.argv))
