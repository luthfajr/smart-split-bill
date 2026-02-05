# Split Bill Application

This repository contains AI-based application for splitting-bill, written on python (streamlit) and can be run on your local computer. 

Courtesy of: https://github.com/MukhlasAdib

## Features

With this application, you can upload a photo of your receipt. The AI will read the receipt and show you the data.

![receipt-data-page](figs/receipt-data-page.jpg)

Then, you can list participants of your split-bill, and then assign items from the receipt to each of them.

![assign-page](figs/assign-page.jpg)

When you are done, final report will be shown.

![report-page](figs/report-page.jpg)

## Installation

1. Make sure Python is installed (any recent version should be fine, I tested with Python 3.12)
2. Create environment for this application

with virtualenv:

```bash
    pip install virtualenv
    python -m virtualenv .ven
```
with uv:

```bash
    uv sync
```

3. Activate the environment

if using Linux

```bash
    source .venv/bin/activate
```

if using Windows

```powershell
    .\.venv\Scripts\activate
```

4. Install required libraries

with virtualenv:

```bash
    pip install -r requirements.txt
```
with uv:

```bash
    uv sync
```

## Run Application

1. Activate the environment

if using Linux

```bash
    source .venv/bin/activate
```

if using Windows

```powershell
    .\.venv\Scripts\activate
```

2. Start the app

with virtualenv:

```bash
    streamlit run app.py
```

with uv:


```bash
    uv run streamlit run app.py
```

## Demo

Below are two samples of receipts read by this application using four models: Gemini, Donut, Florence, and PaddleOCR.

### Receipt 1

![receipt1](demo/receipt1.jpg)

Gemini result:

![gemini1](demo/gemini1.png)

Donut result:

![donut1](demo/donut1.png)

Florence result:

![florence1](demo/florence1.png)

PaddleOCR result:

![paddleocr1](demo/paddleocr1.png)

### Receipt 2

![receipt2](demo/receipt2.jpeg)

Gemini result:

![gemini2](demo/gemini2.png)

Donut result:

![donut2](demo/donut2.png)

Florence result:

![florence2](demo/florence2.png)

PaddleOCR result:

![paddleocr2](demo/paddleocr2.png)