---
configs:
- config_name: default
  data_files:
  - split: train
    path: data/train-*
dataset_info:
  features:
  - name: query
    dtype: string
  - name: pos
    sequence: string
  - name: neg
    sequence: string
  - name: task
    dtype: string
  - name: instruction
    struct:
    - name: query
      dtype: string
    - name: pos
      dtype: string
    - name: neg
      dtype: string
  splits:
  - name: train
    num_bytes: 27977412
    num_examples: 82783
  download_size: 8138135
  dataset_size: 27977412
---
# Dataset Card for "coco_captions_1107"

[More Information needed](https://github.com/huggingface/datasets/blob/main/CONTRIBUTING.md#how-to-contribute-to-the-dataset-cards)