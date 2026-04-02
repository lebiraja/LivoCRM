# AWS Bedrock — Setup & Usage Guide

> A reusable guide for integrating AWS Bedrock into any Python project.
> All API keys are loaded from environment variables — **never hard-code credentials**.

---

## Table of Contents

1. [What is AWS Bedrock?](#what-is-aws-bedrock)
2. [AWS Account Setup](#aws-account-setup)
3. [IAM Permissions](#iam-permissions)
4. [Model Access (Enable Models)](#model-access-enable-models)
5. [Environment Variables Template](#environment-variables-template)
6. [Python Dependencies](#python-dependencies)
7. [Building the Bedrock Client](#building-the-bedrock-client)
8. [API 1: Converse API (Text Generation / LLM)](#api-1-converse-api-text-generation--llm)
9. [API 2: InvokeModel API (Embeddings)](#api-2-invokemodel-api-embeddings)
10. [Available Models](#available-models)
11. [Inference Parameters](#inference-parameters)
12. [Common Patterns](#common-patterns)
13. [Error Handling](#error-handling)
14. [Cost Management](#cost-management)
15. [Troubleshooting](#troubleshooting)

---

## What is AWS Bedrock?

AWS Bedrock is a fully managed service that makes foundation models (FMs) from leading AI companies available through a single API. You don't provision servers or manage GPUs — you just call the API.

**Key advantages**:
- No infrastructure to manage
- Pay-per-token pricing (no idle costs)
- Multiple model providers: Meta (Llama), Anthropic (Claude), Amazon (Titan), Cohere, Mistral
- Two APIs: **Converse** (unified chat/text) and **InvokeModel** (model-specific payloads)

---

## AWS Account Setup

### Step 1: Create an AWS Account
Go to [aws.amazon.com](https://aws.amazon.com) and create an account if you don't have one.

### Step 2: Create an IAM User for API Access

1. Go to **IAM Console** → **Users** → **Create user**
2. Name: `bedrock-api-user` (or your app name)
3. **Attach permissions directly** → search for `AmazonBedrockFullAccess`
4. Create the user
5. Go to the user → **Security credentials** → **Create access key**
6. Select **Application running outside AWS**
7. **Save the Access Key ID and Secret Access Key** — you'll need these for the `.env` file

> ⚠️ **Never commit these keys to git.** Always use `.env` files and add `.env` to `.gitignore`.

### Step 3: Choose a Region

Bedrock is available in specific regions. Popular choices:
- `us-east-1` (N. Virginia) — widest model selection
- `us-west-2` (Oregon)
- `eu-west-1` (Ireland)
- `ap-southeast-1` (Singapore)

Check [Bedrock region availability](https://docs.aws.amazon.com/bedrock/latest/userguide/bedrock-regions.html) for the latest list.

---

## IAM Permissions

### Minimum Required Policy

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel",
        "bedrock:InvokeModelWithResponseStream",
        "bedrock:Converse",
        "bedrock:ConverseStream"
      ],
      "Resource": "arn:aws:bedrock:*::foundation-model/*"
    }
  ]
}
```

### Full Access (Development)

Use the managed policy: `AmazonBedrockFullAccess`

This includes model listing, invocation, and fine-tuning permissions.

---

## Model Access (Enable Models)

**Important**: Even with IAM permissions, you must explicitly enable each model in the Bedrock console.

1. Go to **AWS Console** → **Amazon Bedrock** → **Model access** (left sidebar)
2. Click **Manage model access**
3. Check the models you want to use:
   - ✅ Meta Llama 4 Scout (17B Instruct)
   - ✅ Amazon Titan Embed Text v2
   - ✅ Any others you need
4. Click **Request model access**
5. Most models are instant; some (Anthropic Claude) may take a few minutes

> If you skip this step, you'll get `AccessDeniedException` when calling the API.

---

## Environment Variables Template

Copy this to your `.env` file and fill in the values:

```env
# =============================================================================
# AWS Bedrock Configuration
# =============================================================================

# ── AWS Credentials ──────────────────────────────────────────────────────────
# From IAM → Users → your-user → Security credentials → Access keys
AWS_ACCESS_KEY_ID=your_access_key_id_here
AWS_SECRET_ACCESS_KEY=your_secret_access_key_here

# Session token (only needed for temporary credentials / SSO / assumed roles)
# AWS_SESSION_TOKEN=your_session_token_here

# ── AWS Region ───────────────────────────────────────────────────────────────
# Must be a region where Bedrock is available and your models are enabled
AWS_DEFAULT_REGION=us-east-1

# ── Model IDs ────────────────────────────────────────────────────────────────
# LLM model for text generation (Converse API)
BEDROCK_LLM_MODEL=us.meta.llama4-scout-17b-instruct-v1:0

# Embedding model for vector search / RAG (InvokeModel API)
BEDROCK_EMBEDDING_MODEL=amazon.titan-embed-text-v2:0

# ── Optional: Custom Endpoint ────────────────────────────────────────────────
# Use this if you're routing through a proxy, VPC endpoint, or LocalStack
# BEDROCK_ENDPOINT_URL=https://your-proxy.example.com
```

**Add to `.gitignore`**:
```
.env
.env.local
.env.production
```

---

## Python Dependencies

```bash
pip install boto3
```

Or in `requirements.txt`:
```
boto3>=1.34.0
```

`boto3` is the official AWS SDK for Python. It handles authentication, request signing, retries, and response parsing automatically.

---

## Building the Bedrock Client

This is the reusable client factory pattern used throughout the project:

```python
import boto3
import os

def build_bedrock_client():
    """
    Build a boto3 bedrock-runtime client from environment variables.
    
    Required env vars:
        AWS_ACCESS_KEY_ID
        AWS_SECRET_ACCESS_KEY
        AWS_DEFAULT_REGION
    
    Optional env vars:
        AWS_SESSION_TOKEN      — for temporary credentials
        BEDROCK_ENDPOINT_URL   — custom endpoint (proxy, VPC, LocalStack)
    """
    kwargs = dict(
        service_name="bedrock-runtime",
        region_name=os.getenv("AWS_DEFAULT_REGION", "us-east-1"),
    )

    # Explicit credentials (recommended for Docker / server environments)
    access_key = os.getenv("AWS_ACCESS_KEY_ID")
    secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
    session_token = os.getenv("AWS_SESSION_TOKEN")

    if access_key and secret_key:
        kwargs["aws_access_key_id"] = access_key
        kwargs["aws_secret_access_key"] = secret_key
        if session_token:
            kwargs["aws_session_token"] = session_token

    # Optional custom endpoint
    endpoint = os.getenv("BEDROCK_ENDPOINT_URL")
    if endpoint:
        kwargs["endpoint_url"] = endpoint

    return boto3.client(**kwargs)
```

### How Authentication Works

boto3 checks credentials in this order:
1. **Explicit parameters** (what we pass via env vars above)
2. `~/.aws/credentials` file
3. `~/.aws/config` file
4. EC2/ECS instance metadata (when running on AWS infrastructure)

For local development and Docker, always use explicit env vars.

---

## API 1: Converse API (Text Generation / LLM)

The **Converse API** is the recommended way to call LLM models. It provides a unified interface across all providers (Meta, Anthropic, Amazon, etc.).

### Basic Usage

```python
import os

def invoke_llm(prompt: str, max_tokens: int = 2048) -> str:
    """
    Send a prompt to Bedrock and get a text response.
    
    Uses the Converse API — works with all chat-compatible models:
    Meta Llama, Anthropic Claude, Amazon Titan Text, Mistral, etc.
    """
    client = build_bedrock_client()
    model_id = os.getenv("BEDROCK_LLM_MODEL", "us.meta.llama4-scout-17b-instruct-v1:0")

    response = client.converse(
        modelId=model_id,
        messages=[
            {
                "role": "user",
                "content": [{"text": prompt}],
            }
        ],
        inferenceConfig={
            "maxTokens": max_tokens,
            "temperature": 0.7,
            "topP": 0.9,
        },
    )

    # Extract the text from the response
    return response["output"]["message"]["content"][0]["text"]
```

### Multi-Turn Conversation

```python
def chat(messages: list[dict], max_tokens: int = 2048) -> str:
    """
    Multi-turn conversation with message history.
    
    messages format:
    [
        {"role": "user", "content": [{"text": "Hello"}]},
        {"role": "assistant", "content": [{"text": "Hi there!"}]},
        {"role": "user", "content": [{"text": "What is Python?"}]},
    ]
    """
    client = build_bedrock_client()
    model_id = os.getenv("BEDROCK_LLM_MODEL", "us.meta.llama4-scout-17b-instruct-v1:0")

    response = client.converse(
        modelId=model_id,
        messages=messages,
        inferenceConfig={
            "maxTokens": max_tokens,
            "temperature": 0.7,
            "topP": 0.9,
        },
    )

    return response["output"]["message"]["content"][0]["text"]
```

### With System Prompt

```python
def invoke_with_system(system_prompt: str, user_prompt: str, max_tokens: int = 2048) -> str:
    """Call LLM with a system prompt for persona/instruction setting."""
    client = build_bedrock_client()
    model_id = os.getenv("BEDROCK_LLM_MODEL", "us.meta.llama4-scout-17b-instruct-v1:0")

    response = client.converse(
        modelId=model_id,
        system=[{"text": system_prompt}],
        messages=[
            {"role": "user", "content": [{"text": user_prompt}]}
        ],
        inferenceConfig={
            "maxTokens": max_tokens,
            "temperature": 0.7,
            "topP": 0.9,
        },
    )

    return response["output"]["message"]["content"][0]["text"]
```

### Converse API Response Structure

```python
{
    "output": {
        "message": {
            "role": "assistant",
            "content": [
                {"text": "The response text goes here..."}
            ]
        }
    },
    "usage": {
        "inputTokens": 150,
        "outputTokens": 300,
        "totalTokens": 450
    },
    "stopReason": "end_turn",    # or "max_tokens", "stop_sequence"
    "metrics": {
        "latencyMs": 1234
    }
}
```

### Getting Token Usage

```python
response = client.converse(...)
usage = response.get("usage", {})
print(f"Input tokens:  {usage.get('inputTokens', 0)}")
print(f"Output tokens: {usage.get('outputTokens', 0)}")
print(f"Total tokens:  {usage.get('totalTokens', 0)}")
```

---

## API 2: InvokeModel API (Embeddings)

The **InvokeModel API** is used for model-specific operations like embeddings. Each model has its own request/response format.

### Amazon Titan Embed Text

```python
import json

def embed_text(text: str) -> list[float]:
    """
    Generate an embedding vector for a text string.
    Uses Amazon Titan Embed Text v2.
    
    Returns: list of floats (1024 dimensions for v2)
    """
    client = build_bedrock_client()
    model_id = os.getenv("BEDROCK_EMBEDDING_MODEL", "amazon.titan-embed-text-v2:0")

    response = client.invoke_model(
        modelId=model_id,
        contentType="application/json",
        accept="application/json",
        body=json.dumps({"inputText": text}),
    )

    result = json.loads(response["body"].read())
    return result["embedding"]  # list of 1024 floats
```

### Batch Embeddings

```python
def embed_documents(texts: list[str]) -> list[list[float]]:
    """Embed multiple texts. Titan doesn't support batch, so we loop."""
    embeddings = []
    for text in texts:
        vec = embed_text(text)
        if vec:
            embeddings.append(vec)
    return embeddings
```

### Titan Embed Request/Response Format

**Request**:
```json
{
    "inputText": "Your text to embed here"
}
```

**Response**:
```json
{
    "embedding": [0.123, -0.456, 0.789, ...],  // 1024 floats (v2) or 1536 floats (v1)
    "inputTextTokenCount": 5
}
```

---

## Available Models

### LLM Models (Converse API)

| Model ID | Provider | Context Window | Best For |
|----------|----------|---------------|----------|
| `us.meta.llama4-scout-17b-instruct-v1:0` | Meta | 128K | General purpose, fast |
| `us.meta.llama4-maverick-17b-instruct-v1:0` | Meta | 128K | Creative, longer outputs |
| `anthropic.claude-3-5-sonnet-20241022-v2:0` | Anthropic | 200K | Complex reasoning, code |
| `anthropic.claude-3-haiku-20240307-v1:0` | Anthropic | 200K | Fast, cheap |
| `amazon.titan-text-premier-v1:0` | Amazon | 32K | General purpose |
| `mistral.mistral-large-2407-v1:0` | Mistral | 128K | Code, European languages |

### Embedding Models (InvokeModel API)

| Model ID | Provider | Dimensions | Max Input |
|----------|----------|-----------|-----------|
| `amazon.titan-embed-text-v2:0` | Amazon | 1024 | 8192 tokens |
| `amazon.titan-embed-text-v1` | Amazon | 1536 | 8192 tokens |
| `cohere.embed-english-v3` | Cohere | 1024 | 512 tokens |
| `cohere.embed-multilingual-v3` | Cohere | 1024 | 512 tokens |

> **Model IDs may vary by region.** Some models have region-specific prefixes (e.g., `us.meta.llama4-*`). Check the Bedrock console in your region for exact IDs.

### ⭐ Recommended Models (Battle-Tested in Production)

These are the exact models used in **CareerWise AI** and recommended for new projects:

#### LLM: Meta Llama 4 Scout 17B Instruct

```
Model ID:  us.meta.llama4-scout-17b-instruct-v1:0
Provider:  Meta
API:       Converse API (client.converse())
Context:   128K tokens
Pricing:   ~$0.17 / 1M tokens (input & output)
```

**Why this model**:
- **Cheapest option** — 18× cheaper than Claude 3.5 Sonnet for comparable quality
- **128K context window** — handles long resumes, full GitHub profiles, and multi-turn conversations
- **Fast inference** — low latency for real-time applications
- **Great at structured output** — reliably returns JSON, markdown tables, scored analysis
- **No special request format** — works with the standard Converse API (same code works for Claude, Titan, etc.)

**Used in this codebase for**:
| File | Use Case |
|------|----------|
| `mentor_brain.py` | Career advice (fit analysis, roadmap, project suggestions, summary) |
| `resume_parser.py` | Resume text → structured JSON extraction |
| `github_analyzer.py` | GitHub profile analysis and scoring |
| `rag_chat_bedrock.py` | RAG-powered AI mentor chat |
| `task_pipeline.py` | Task description LLM refinement |
| `project_evaluator.py` | GitHub repo evaluation and scoring |

#### Embeddings: Amazon Titan Embed Text v2

```
Model ID:  amazon.titan-embed-text-v2:0
Provider:  Amazon
API:       InvokeModel API (client.invoke_model())
Dimensions: 1024
Max Input: 8,192 tokens
Pricing:   ~$0.02 / 1M tokens
```

**Why this model**:
- **Native AWS model** — no model access request needed, instant availability
- **Dirt cheap** — $0.02 per million tokens (essentially free for dev usage)
- **1024 dimensions** — good balance of quality vs storage/compute cost
- **8K token input** — can embed entire documents, not just sentences
- **Simple API** — just `{"inputText": "your text"}`, returns `{"embedding": [...]}`

**Used in this codebase for**:
| File | Use Case |
|------|----------|
| `rag_chat_bedrock.py` | Embedding resume text + analysis for vector search (RAG) |

#### Quick Setup — Copy These to Your `.env`

```env
# ── Recommended Bedrock Models ────────────────────────────────────────────────
# LLM (text generation, chat, analysis)
BEDROCK_LLM_MODEL=us.meta.llama4-scout-17b-instruct-v1:0

# Embeddings (vector search, RAG, similarity)
BEDROCK_EMBEDDING_MODEL=amazon.titan-embed-text-v2:0
```

---

## Inference Parameters

| Parameter | Type | Range | Description |
|-----------|------|-------|-------------|
| `maxTokens` | int | 1 - 4096+ | Maximum response length |
| `temperature` | float | 0.0 - 1.0 | Randomness (0 = deterministic, 1 = creative) |
| `topP` | float | 0.0 - 1.0 | Nucleus sampling (0.9 = consider top 90% probability tokens) |
| `stopSequences` | list[str] | — | Stop generating when these strings are produced |

### Recommended Settings

| Use Case | temperature | topP | maxTokens |
|----------|-------------|------|-----------|
| Code generation | 0.1 - 0.3 | 0.9 | 2048 |
| Structured JSON output | 0.0 - 0.2 | 0.9 | 1024 |
| Creative writing | 0.7 - 0.9 | 0.95 | 2048 |
| Analysis / scoring | 0.3 - 0.5 | 0.9 | 1000 |
| Career advice (this project) | 0.7 | 0.9 | 700 - 1200 |

---

## Common Patterns

### Pattern 1: Structured JSON Output

```python
import json

def get_structured_output(data: dict) -> dict:
    """Ask the LLM to return structured JSON."""
    prompt = f"""Analyze the following data and respond with ONLY valid JSON.
No explanation, no markdown, just JSON.

Data: {json.dumps(data)}

Required JSON format:
{{
    "score": <int 1-10>,
    "feedback": "<string>",
    "tags": ["<string>"]
}}"""

    raw = invoke_llm(prompt, max_tokens=500)

    # Clean up markdown code fences if present
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[1]  # remove first line
        cleaned = cleaned.rsplit("```", 1)[0]  # remove last fence

    return json.loads(cleaned)
```

### Pattern 2: Concurrent LLM Calls

```python
from concurrent.futures import ThreadPoolExecutor

def analyze_parallel(resume_data, github_data):
    """Run multiple independent LLM calls concurrently."""
    with ThreadPoolExecutor(max_workers=4) as executor:
        future_fit = executor.submit(analyze_fit, resume_data)
        future_roadmap = executor.submit(generate_roadmap, resume_data)
        future_projects = executor.submit(suggest_projects, github_data)

        fit = future_fit.result()        # blocks until done
        roadmap = future_roadmap.result()
        projects = future_projects.result()

    return {"fit": fit, "roadmap": roadmap, "projects": projects}
```

### Pattern 3: Retry with Fallback

```python
import time

def invoke_llm_safe(prompt: str, max_retries: int = 3) -> str:
    """LLM call with retry logic and graceful fallback."""
    for attempt in range(max_retries):
        try:
            return invoke_llm(prompt)
        except client.exceptions.ThrottlingException:
            wait = 2 ** attempt  # exponential backoff: 1s, 2s, 4s
            print(f"⚠️  Rate limited, retrying in {wait}s...")
            time.sleep(wait)
        except client.exceptions.ModelNotReadyException:
            print("⚠️  Model warming up, retrying in 5s...")
            time.sleep(5)
        except Exception as exc:
            print(f"⚠️  LLM error: {exc}")
            break

    return "AI analysis temporarily unavailable."
```

### Pattern 4: RAG (Retrieval-Augmented Generation)

```python
def rag_query(question: str, context_docs: list[str]) -> str:
    """Answer a question using retrieved context documents."""
    context = "\n\n---\n\n".join(context_docs)

    prompt = f"""Answer the question based ONLY on the provided context.
If the context doesn't contain the answer, say "I don't have enough information."

CONTEXT:
{context}

QUESTION: {question}

ANSWER:"""

    return invoke_llm(prompt, max_tokens=1000)
```

---

## Error Handling

### Common Exceptions

```python
import botocore.exceptions

try:
    response = invoke_llm("Hello")
except botocore.exceptions.ClientError as e:
    error_code = e.response["Error"]["Code"]

    if error_code == "AccessDeniedException":
        print("❌ Model not enabled in Bedrock console, or IAM permissions missing")
    elif error_code == "ValidationException":
        print("❌ Invalid model ID or request format")
    elif error_code == "ThrottlingException":
        print("⚠️  Rate limited — slow down or request a quota increase")
    elif error_code == "ModelNotReadyException":
        print("⚠️  Model is warming up — retry in a few seconds")
    elif error_code == "ServiceUnavailableException":
        print("⚠️  Bedrock service temporarily unavailable")
    else:
        print(f"❌ AWS error: {error_code} — {e}")

except botocore.exceptions.NoCredentialsError:
    print("❌ No AWS credentials found. Check your .env file")

except botocore.exceptions.EndpointConnectionError:
    print("❌ Cannot connect to Bedrock endpoint. Check region and network")
```

---

## Cost Management

### Pricing Model
Bedrock uses **pay-per-token** pricing. No idle costs.

| Model | Input (per 1M tokens) | Output (per 1M tokens) |
|-------|-----------------------|------------------------|
| Llama 4 Scout 17B | ~$0.17 | ~$0.17 |
| Claude 3.5 Sonnet | ~$3.00 | ~$15.00 |
| Claude 3 Haiku | ~$0.25 | ~$1.25 |
| Titan Text Premier | ~$0.50 | ~$1.50 |
| Titan Embed Text v2 | ~$0.02 | N/A |

> Prices vary by region. Check [Bedrock pricing](https://aws.amazon.com/bedrock/pricing/) for current rates.

### Cost Optimization Tips

1. **Use `maxTokens` wisely** — don't set it to 4096 if you expect 200 words
2. **Choose the right model** — Llama 4 Scout is 18× cheaper than Claude 3.5 Sonnet
3. **Cache responses** — identical prompts return identical tokens, so cache them
4. **Run concurrent calls** — parallelism doesn't cost more, it just saves time
5. **Monitor usage** — use AWS CloudWatch or Cost Explorer to track spending

### Set Budget Alerts

1. Go to **AWS Billing** → **Budgets** → **Create budget**
2. Set a monthly budget (e.g., $10 for development)
3. Add email alerts at 80% and 100% thresholds

---

## Troubleshooting

| Error | Cause | Fix |
|-------|-------|-----|
| `NoCredentialsError` | AWS keys not set | Check `.env` has `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` |
| `AccessDeniedException` | Model not enabled or IAM issue | Enable model in Bedrock console; check IAM policy |
| `ValidationException` | Wrong model ID | Check exact model ID in Bedrock console for your region |
| `ThrottlingException` | Too many requests | Add retry logic with exponential backoff |
| `ModelNotReadyException` | Cold start | Retry after 5 seconds |
| `EndpointConnectionError` | Wrong region or no network | Check `AWS_DEFAULT_REGION` matches where models are enabled |
| `ModelTimeoutException` | Prompt too long or model overloaded | Reduce prompt size; retry |
| Empty response | Model returned no content | Check `stopReason` — may be `max_tokens` (increase limit) |

### Quick Verification Script

Save this as `test_bedrock.py` and run to verify your setup:

```python
#!/usr/bin/env python3
"""Quick test to verify AWS Bedrock connectivity."""

import os
import json
import boto3
from dotenv import load_dotenv

load_dotenv()

def test_bedrock():
    print("🔍 Testing AWS Bedrock connection...\n")

    # 1. Check credentials
    ak = os.getenv("AWS_ACCESS_KEY_ID")
    sk = os.getenv("AWS_SECRET_ACCESS_KEY")
    region = os.getenv("AWS_DEFAULT_REGION", "us-east-1")

    if not ak or not sk:
        print("❌ AWS_ACCESS_KEY_ID or AWS_SECRET_ACCESS_KEY not set in .env")
        return

    print(f"  Region:      {region}")
    print(f"  Access Key:  {ak[:4]}...{ak[-4:]}")

    # 2. Build client
    client = boto3.client(
        service_name="bedrock-runtime",
        region_name=region,
        aws_access_key_id=ak,
        aws_secret_access_key=sk,
    )

    # 3. Test LLM (Converse API)
    llm_model = os.getenv("BEDROCK_LLM_MODEL", "us.meta.llama4-scout-17b-instruct-v1:0")
    print(f"\n📝 Testing LLM: {llm_model}")
    try:
        resp = client.converse(
            modelId=llm_model,
            messages=[{"role": "user", "content": [{"text": "Say hello in one word."}]}],
            inferenceConfig={"maxTokens": 10, "temperature": 0.1},
        )
        text = resp["output"]["message"]["content"][0]["text"]
        tokens = resp.get("usage", {}).get("totalTokens", "?")
        print(f"  ✅ LLM response: {text.strip()}")
        print(f"  📊 Tokens used: {tokens}")
    except Exception as e:
        print(f"  ❌ LLM test failed: {e}")

    # 4. Test Embeddings (InvokeModel API)
    embed_model = os.getenv("BEDROCK_EMBEDDING_MODEL", "amazon.titan-embed-text-v2:0")
    print(f"\n🧮 Testing Embeddings: {embed_model}")
    try:
        resp = client.invoke_model(
            modelId=embed_model,
            contentType="application/json",
            accept="application/json",
            body=json.dumps({"inputText": "test"}),
        )
        result = json.loads(resp["body"].read())
        dims = len(result["embedding"])
        print(f"  ✅ Embedding dimensions: {dims}")
    except Exception as e:
        print(f"  ❌ Embedding test failed: {e}")

    print("\n✅ Bedrock verification complete!")

if __name__ == "__main__":
    test_bedrock()
```

Run it:
```bash
pip install boto3 python-dotenv
python test_bedrock.py
```
