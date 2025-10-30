# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

DeepSeek-OCR is an optical character recognition (OCR) model that investigates the role of vision encoders from an LLM-centric viewpoint. It supports document parsing, OCR, and layout detection with efficient visual-text compression. The model is available at `deepseek-ai/DeepSeek-OCR` on HuggingFace.

## Environment Setup

### Prerequisites
- CUDA 11.8 + PyTorch 2.6.0
- Python 3.12.9

### Installation Commands

```bash
# Create and activate conda environment
conda create -n deepseek-ocr python=3.12.9 -y
conda activate deepseek-ocr

# Install PyTorch with CUDA 11.8
pip install torch==2.6.0 torchvision==0.21.0 torchaudio==2.6.0 --index-url https://download.pytorch.org/whl/cu118

# Install vLLM (download whl from https://github.com/vllm-project/vllm/releases/tag/v0.8.5)
pip install vllm-0.8.5+cu118-cp38-abi3-manylinux1_x86_64.whl

# Install dependencies
pip install -r requirements.txt

# Install flash attention
pip install flash-attn==2.7.3 --no-build-isolation
```

**Note:** vLLM and transformers can run in the same environment despite dependency warnings.

## Architecture

### Two Inference Backends

The codebase supports two inference approaches:

1. **vLLM Backend** (`DeepSeek-OCR-master/DeepSeek-OCR-vllm/`):
   - High-performance batch inference with concurrency support
   - Custom vLLM model implementation in `deepseek_ocr.py`
   - Three main scripts:
     - `run_dpsk_ocr_image.py` - Single image streaming inference
     - `run_dpsk_ocr_pdf.py` - PDF processing with ~2500 tokens/s on A100-40G
     - `run_dpsk_ocr_eval_batch.py` - Batch evaluation for benchmarks

2. **Transformers Backend** (`DeepSeek-OCR-master/DeepSeek-OCR-hf/`):
   - Standard HuggingFace transformers interface
   - Simpler API via `model.infer()` method
   - `run_dpsk_ocr.py` - Basic inference script

### Vision Architecture

The model uses a dual-encoder architecture combining:
- SAM (Segment Anything Model) encoder (`deepencoder/sam_vary_sdpa.py`)
- CLIP-L encoder (`deepencoder/clip_sdpa.py`)
- MLP projector (`deepencoder/build_linear.py`) to map concatenated features to LLM embedding space

Features from both encoders are concatenated and projected before being merged with text tokens in the language model.

### Resolution Modes

Configured via `BASE_SIZE`, `IMAGE_SIZE`, and `CROP_MODE` in `config.py`:

- **Tiny**: `base_size=512, image_size=512, crop_mode=False` (64 vision tokens)
- **Small**: `base_size=640, image_size=640, crop_mode=False` (100 vision tokens)
- **Base**: `base_size=1024, image_size=1024, crop_mode=False` (256 vision tokens)
- **Large**: `base_size=1280, image_size=1280, crop_mode=False` (400 vision tokens)
- **Gundam** (Dynamic): `base_size=1024, image_size=640, crop_mode=True` - Splits images into n×640×640 patches + 1×1024×1024 global view

### Image Processing Pipeline

`process/image_process.py` contains the core preprocessing logic:

1. `dynamic_preprocess()` - Dynamically splits images into optimal tile grid based on aspect ratio
2. `count_tiles()` - Calculates tile configuration (controlled by `MIN_CROPS` and `MAX_CROPS`)
3. `ImageTransform` - Normalizes images with mean=(0.5, 0.5, 0.5), std=(0.5, 0.5, 0.5)
4. `DeepseekOCRProcessor` - Main processor that:
   - Tokenizes text with `<image>` placeholder tokens
   - Generates global view (padded to `BASE_SIZE`)
   - Generates local views (tiled crops at `IMAGE_SIZE`)
   - Creates spatial crop metadata for position tracking

### N-gram Repetition Prevention

`process/ngram_norepeat.py` implements `NoRepeatNGramLogitsProcessor` to prevent repetitive text generation during OCR, with configurable:
- `ngram_size` - Size of n-grams to track
- `window_size` - Lookback window
- `whitelist_token_ids` - Tokens exempt from blocking (e.g., table tags `<td>`, `</td>`)

## Running Inference

### Configuration

All runs require editing `DeepSeek-OCR-master/DeepSeek-OCR-vllm/config.py`:

```python
MODEL_PATH = 'deepseek-ai/DeepSeek-OCR'  # or local path
INPUT_PATH = ''   # Set input file/directory path
OUTPUT_PATH = ''  # Set output directory path
PROMPT = '<image>\n<|grounding|>Convert the document to markdown.'  # Choose prompt
```

### vLLM Inference

```bash
cd DeepSeek-OCR-master/DeepSeek-OCR-vllm

# Single image with streaming output
python run_dpsk_ocr_image.py

# PDF processing (concurrent batching)
python run_dpsk_ocr_pdf.py

# Batch evaluation for benchmarks
python run_dpsk_ocr_eval_batch.py
```

**Key vLLM Parameters:**
- `MAX_CONCURRENCY` - Number of concurrent requests (default: 100)
- `NUM_WORKERS` - Image preprocessing workers (default: 64)
- `gpu_memory_utilization` - GPU memory fraction (0.75 for image, 0.9 for PDF/batch)

### Transformers Inference

```bash
cd DeepSeek-OCR-master/DeepSeek-OCR-hf
python run_dpsk_ocr.py
```

Edit the script to configure:
- `prompt` - Task prompt
- `image_file` - Input image path
- `output_path` - Output directory
- Resolution parameters: `base_size`, `image_size`, `crop_mode`

### Common Prompt Patterns

```python
# Document conversion with layout detection
"<image>\n<|grounding|>Convert the document to markdown."

# General OCR with layout
"<image>\n<|grounding|>OCR this image."

# Plain OCR without layout structure
"<image>\nFree OCR."

# Figure/chart parsing
"<image>\nParse the figure."

# General image description
"<image>\nDescribe this image in detail."

# Grounding/localization
"<image>\nLocate <|ref|>xxxx<|/ref|> in the image."
```

## Output Format

The model outputs markdown text with special tokens:

- `<|ref|>label<|/ref|><|det|>coordinates<|/det|>` - Grounding annotations with bounding boxes
- Coordinates are normalized to 0-999 scale
- Image regions are extracted and saved when `<|ref|>image<|/ref|>` appears
- Post-processing regex patterns remove grounding tokens and extract clean markdown

Both PDF and image scripts generate:
- `result_ori.mmd` or `*_det.mmd` - Raw output with grounding tokens
- `result.mmd` or `*.mmd` - Cleaned markdown with bounding box references removed
- `result_with_boxes.jpg` or `*_layouts.pdf` - Visualization with drawn bounding boxes
- `images/` directory - Extracted image regions

## Model Registration

vLLM requires custom model registration before use:

```python
from vllm.model_executor.models.registry import ModelRegistry
from deepseek_ocr import DeepseekOCRForCausalLM

ModelRegistry.register_model("DeepseekOCRForCausalLM", DeepseekOCRForCausalLM)
```

## Upstream vLLM Support

As of 2025/10/23, DeepSeek-OCR is officially supported in upstream vLLM (v0.11.1+). See README.md for the simpler upstream usage pattern with `vllm.LLM` and `NGramPerReqLogitsProcessor`.
