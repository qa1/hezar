from dataclasses import dataclass, field
from typing import List

import torch
from datasets import load_dataset

from ...configs import DatasetConfig
from ...preprocessors.tokenizers import Tokenizer
from ...registry import register_dataset
from ..data_collators import TextPaddingDataCollator
from .dataset import Dataset


@dataclass
class TextClassificationDatasetConfig(DatasetConfig):
    name: str = "text_classification"
    task: str = "text_classification"
    path: str = None
    preprocessors: List[str] = field(default_factory=list)
    tokenizer_path: str = None
    label_field: str = None
    text_field: str = None
    max_length: int = None


@register_dataset("text_classification", config_class=TextClassificationDatasetConfig)
class TextClassificationDataset(Dataset):
    def __init__(self, config: TextClassificationDatasetConfig, split=None, **kwargs):
        super().__init__(config, **kwargs)
        self.dataset = self._load(split)
        self._extract_labels()
        self.preprocessor = Tokenizer.load(self.config.tokenizer_path)
        self.data_collator = TextPaddingDataCollator(
            tokenizer=self.preprocessor,
            max_length=self.config.max_length,
        )

    def _load(self, split):
        dataset = load_dataset(self.config.path, split=split)
        return dataset

    def _extract_labels(self):
        labels_list = self.dataset.features[self.config.label_field].names
        self.id2label = self.config.id2label = {str(k): str(v) for k, v in dict(list(enumerate(labels_list))).items()}
        self.label2id = self.config.label2id = {v: k for k, v in self.id2label.items()}
        self.num_labels = self.config.num_labels = len(labels_list)

    def __len__(self):
        return len(self.dataset)

    def __getitem__(self, index):
        text = self.dataset[index][self.config.text_field]
        label = self.dataset[index][self.config.label_field]
        inputs = self.preprocessor(
            text,
            return_tensors="pt",
            truncation_strategy="longest_first",
            padding="longest",
            return_attention_mask=True,
        )
        label_idx = torch.tensor([label], dtype=torch.long)  # noqa
        inputs["labels"] = label_idx

        return inputs
