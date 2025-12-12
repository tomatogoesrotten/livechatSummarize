# LiveChat Summarization App

AI-powered chat summarization for LiveChat with automatic ticket creation and CRM integration.

## Features

- **Dual Trigger System**: Automatically summarize on chat end or via agent button
- **AI Summarization**: Uses OpenAI GPT-4 for intelligent conversation analysis
- **Custom Filtering**: Configurable rules to remove unwanted content before summarization
- **Ticket Creation**: Automatically creates LiveChat tickets from chats
- **CRM Integration**: Sends summaries to your CRM via REST API or webhooks

## Architecture

```
┌─────────────────┐     ┌──────────────────────┐     ┌─────────────────┐
│   LiveChat      │────▶│   FastAPI Backend    │────▶│   OpenAI        │
│   (Webhook/     │     │   - Webhook Handler  │     │   (GPT-4)       │
│    Button)      │     │   - Filter Service   │     └─────────────────┘
└─────────────────┘     │   - Summarizer       │            │
                        │   - CRM Client       │◀───────────┘
                        └──────────┬───────────┘
                                   │
                                   ▼
                        ┌─────────────────────┐
                        │   Your CRM          │
                        │   (REST/Webhook)    │
                        └─────────────────────┘
```

## Quick Start

### 1. Clone and Install

```bash
git clone <repository-url>
cd livechatSummarize

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment

Copy `env.example` to `.env` and fill in your credentials:

```bash
cp env.example .env
```

Required settings:
- `LIVECHAT_CLIENT_ID` - From LiveChat Developer Console
- `LIVECHAT_CLIENT_SECRET` - From LiveChat Developer Console
- `OPENAI_API_KEY` - From OpenAI Platform
- `CRM_ENDPOINT_URL` - Your CRM API endpoint

### 3. Run the Server

```bash
# Development mode
python -m app.main

# Or with uvicorn directly
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 4. Configure LiveChat App

1. Go to [LiveChat Developer Console](https://developers.livechat.com/console/)
2. Create a new app or update existing one
3. Configure webhooks:
   - Add `chat_deactivated` webhook pointing to `https://your-domain.com/webhooks/livechat`
4. Configure Agent App Widget:
   - URL: `https://your-domain.com/widget/index.html`
5. Add required scopes: `chats--all:ro`, `tickets--all:rw`, `agents--all:ro`
6. Install the app on your LiveChat account

## API Endpoints

### Webhooks

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/webhooks/livechat` | POST | Receives LiveChat webhook events |
| `/webhooks/health` | GET | Webhook endpoint health check |

### Actions

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/summarize` | POST | Manual summarization trigger |
| `/api/summarize/{chat_id}` | GET | Summarize a specific chat |
| `/api/preview/{chat_id}` | GET | Preview summary without actions |
| `/api/status` | GET | Check service configuration status |

### Health

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Root health check |
| `/health` | GET | Health check endpoint |

## Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `LIVECHAT_CLIENT_ID` | Yes | - | OAuth client ID |
| `LIVECHAT_CLIENT_SECRET` | Yes | - | OAuth client secret |
| `OPENAI_API_KEY` | Yes | - | OpenAI API key |
| `OPENAI_MODEL` | No | `gpt-4-turbo-preview` | Model to use |
| `CRM_ENDPOINT_URL` | No | - | CRM API endpoint |
| `CRM_API_KEY` | No | - | CRM authentication key |
| `CRM_USE_WEBHOOK` | No | `false` | Use webhook mode |
| `AUTO_CREATE_TICKET` | No | `true` | Auto-create tickets |
| `AUTO_SEND_TO_CRM` | No | `true` | Auto-send to CRM |

### Filter Rules

| Variable | Default | Description |
|----------|---------|-------------|
| `FILTER_REMOVE_SYSTEM_MESSAGES` | `true` | Remove system messages |
| `FILTER_REMOVE_AGENT_SIGNATURES` | `true` | Remove signature blocks |
| `FILTER_MIN_MESSAGE_LENGTH` | `3` | Minimum message length |
| `FILTER_INCLUDE_GREETINGS` | `true` | Keep simple greetings |

## CRM Payload Structure

```json
{
    "ticket_id": "LC-12345",
    "chat_id": "abc123xyz",
    "customer_email": "customer@example.com",
    "customer_name": "John Doe",
    "summary": "Customer inquired about product pricing...",
    "key_issues": [
        "Pricing question",
        "Feature availability"
    ],
    "resolution": "Agent provided pricing details and feature roadmap",
    "action_items": [
        "Follow up with detailed quote"
    ],
    "sentiment": "positive",
    "urgency": "normal",
    "timestamp": "2025-12-12T10:30:00Z"
}
```

## Deployment

### Railway (Recommended)

1. Connect your GitHub repository to Railway
2. Add environment variables in Railway dashboard
3. Railway will auto-deploy on push

### Render

1. Create a new Web Service on Render
2. Connect your repository
3. Set build command: `pip install -r requirements.txt`
4. Set start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
5. Add environment variables

### Docker

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## Project Structure

```
livechatSummarize/
├── app/
│   ├── __init__.py          # App initialization
│   ├── main.py               # FastAPI application
│   ├── config.py             # Settings and configuration
│   ├── routers/
│   │   ├── webhooks.py       # Webhook endpoints
│   │   └── actions.py        # Manual action endpoints
│   ├── services/
│   │   ├── livechat.py       # LiveChat API client
│   │   ├── summarizer.py     # OpenAI summarization
│   │   ├── filter.py         # Message filtering
│   │   └── crm.py            # CRM integration
│   └── models/
│       └── schemas.py        # Pydantic models
├── widget/
│   └── index.html            # Agent widget UI
├── requirements.txt
├── env.example
├── livechat.config.json
└── README.md
```

## License

MIT License - See LICENSE file for details
