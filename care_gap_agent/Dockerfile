# care_gap_agent — container image
#
# Local build + run:
#   docker build -t care-gap-agent .
#   docker run --rm -p 8001:8001 \
#     -e GOOGLE_API_KEY=your-key \
#     -e MCP_SERVER_URL=http://host.docker.internal:9000/mcp \
#     -e API_KEY_PRIMARY=demo-key \
#     care-gap-agent

FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PORT=8001
ENV AGENT_MODULE=care_gap_agent.app:a2a_app

CMD ["sh", "-c", "exec uvicorn ${AGENT_MODULE} --host 0.0.0.0 --port ${PORT}"]
