"""
Tool for querying RAG Studio knowledge bases.
Supports querying documents from specific knowledge bases (data sources).
"""

import json
import argparse
import requests
from typing import Literal, Optional, Dict, List
from pydantic import BaseModel, Field


class UserParameters(BaseModel):
    """
    Args:
        base_url (str): The base URL of the RAG Studio (e.g., 'https://ragstudio-xxx.cloudera.site').
        api_key (str): API key for authentication.
        knowledge_base_name (str): Name of the default knowledge base (data source) to query.
        project_id (int): The project ID for session creation.
        inference_model (Optional[str]): The inference model to use for generating responses.
        response_chunks (int): Number of chunks to return in responses.
        timeout_seconds (int): HTTP timeout in seconds.
    """
    base_url: str = Field(description="The base URL of the RAG Studio API")
    api_key: str = Field(description="API key for RAG Studio authentication")
    knowledge_base_name: str = Field(description="Name of the knowledge base (data source) to query (e.g., 'Local Companies')")
    project_id: int = Field(default=1, description="The project ID for session creation")
    inference_model: Optional[str] = Field(default=None, description="The inference model to use (e.g., 'gpt-4')")
    response_chunks: int = Field(default=5, description="Number of chunks to return in responses (default: 5)")
    timeout_seconds: int = Field(default=60, description="HTTP timeout in seconds")


class ToolParameters(BaseModel):
    action: Literal["query", "list_knowledge_bases", "get_chat_history", "get_sessions", "upload_document"] = Field(
        description="Action to perform: 'query' (search the knowledge base), 'list_knowledge_bases' (list all knowledge bases), 'get_chat_history' (get chat history with evaluations for a session), 'get_sessions' (list all sessions), 'upload_document' (upload a document to a knowledge base)"
    )

    # Query parameters
    query: Optional[str] = Field(
        default=None,
        description="The question or search query to send to the RAG system (required for 'query' action)"
    )

    # Session ID for chat history
    session_id: Optional[int] = Field(
        default=None,
        description="Session ID for 'get_chat_history' action"
    )

    # Document upload parameters
    file_path: Optional[str] = Field(
        default=None,
        description="Local file path of the document to upload (required for 'upload_document' action)"
    )


def _build_headers(api_key: str) -> Dict[str, str]:
    """Build request headers with authentication."""
    return {
        'Content-Type': 'application/json',
        'accept': 'application/json',
        'Authorization': f'Bearer {api_key}'
    }


def _make_request(method: str, url: str, headers: Dict[str, str],
                  json_data: Optional[Dict] = None, timeout: int = 60) -> requests.Response:
    """Make HTTP request with redirect following."""
    if method == "GET":
        return requests.get(url, headers=headers, timeout=timeout, allow_redirects=True)
    elif method == "POST":
        return requests.post(url, headers=headers, json=json_data, timeout=timeout, allow_redirects=True)
    elif method == "DELETE":
        return requests.delete(url, headers=headers, timeout=timeout, allow_redirects=True)
    else:
        raise ValueError(f"Unsupported HTTP method: {method}")


def get_data_sources(base_url: str, headers: Dict[str, str], timeout: int) -> List[Dict]:
    """Get all available data sources (knowledge bases)."""
    endpoint = f"{base_url}/api/v1/rag/dataSources"
    response = _make_request("GET", endpoint, headers, timeout=timeout)
    response.raise_for_status()
    return response.json()


def find_data_source_by_name(data_sources: List[Dict], name: str) -> Optional[Dict]:
    """Find a data source by name (case-insensitive partial match)."""
    name_lower = name.lower()
    # First try exact match
    for ds in data_sources:
        if ds.get('name', '').lower() == name_lower:
            return ds
    # Then try partial match
    for ds in data_sources:
        if name_lower in ds.get('name', '').lower():
            return ds
    return None


def create_session(base_url: str, headers: Dict[str, str],
                   data_source_ids: List[int], project_id: int,
                   inference_model: Optional[str], response_chunks: int,
                   timeout: int) -> Dict:
    """Create a new RAG session."""
    endpoint = f"{base_url}/api/v1/rag/sessions"
    payload = {
        "name": "Query Session",
        "dataSourceIds": data_source_ids,
        "projectId": project_id,
        "responseChunks": response_chunks,
        "queryConfiguration": {
            "disableStreaming": False
        }
    }
    if inference_model:
        payload["inferenceModel"] = inference_model

    response = _make_request("POST", endpoint, headers, json_data=payload, timeout=timeout)
    response.raise_for_status()
    return response.json()


def get_sessions(base_url: str, headers: Dict[str, str], timeout: int) -> List[Dict]:
    """Get all available sessions."""
    endpoint = f"{base_url}/api/v1/rag/sessions"
    response = _make_request("GET", endpoint, headers, timeout=timeout)
    response.raise_for_status()
    return response.json()


def get_chat_history(base_url: str, headers: Dict[str, str],
                     session_id: int, timeout: int) -> Dict:
    """Get chat history for a session, including evaluations."""
    endpoint = f"{base_url}/llm-service/sessions/{session_id}/chat-history"
    response = _make_request("GET", endpoint, headers, timeout=timeout)
    response.raise_for_status()
    return response.json()


def upload_document(base_url: str, api_key: str, data_source_id: int,
                    file_path: str, timeout: int) -> Dict:
    """Upload a document to a knowledge base (data source)."""
    import os

    endpoint = f"{base_url}/api/v1/rag/dataSources/{data_source_id}/files"

    # Prepare headers for multipart upload (no Content-Type, let requests set it)
    headers = {
        'accept': 'application/json',
        'Authorization': f'Bearer {api_key}'
    }

    # Prepare the file for upload
    filename = os.path.basename(file_path)
    with open(file_path, 'rb') as f:
        files = {'file': (filename, f)}
        response = requests.post(
            endpoint, headers=headers, files=files,
            timeout=timeout, allow_redirects=True
        )

    response.raise_for_status()
    return response.json()


def delete_session(base_url: str, headers: Dict[str, str], session_id: int, timeout: int):
    """Delete a RAG session."""
    endpoint = f"{base_url}/api/v1/rag/sessions/{session_id}"
    try:
        _make_request("DELETE", endpoint, headers, timeout=timeout)
    except:
        pass  # Ignore deletion errors


def send_chat_message(base_url: str, headers: Dict[str, str], session_id: int,
                      message: str, timeout: int) -> Dict:
    """Send a chat message to a RAG session and get the response via streaming endpoint."""
    endpoint = f"{base_url}/llm-service/sessions/{session_id}/stream-completion"
    payload = {
        "query": message
    }

    # Use streaming response
    response = requests.post(
        endpoint, headers=headers, json=payload,
        timeout=timeout, allow_redirects=True, stream=True
    )
    response.raise_for_status()

    # Collect streamed response chunks
    full_response = []
    sources = []
    response_id = None

    for line in response.iter_lines(decode_unicode=True):
        if not line:
            continue

        # Handle SSE format (data: {...})
        if line.startswith("data:"):
            line = line[5:].strip()

        if not line or line == "[DONE]":
            continue

        try:
            chunk = json.loads(line)
            if isinstance(chunk, dict):
                # Skip event messages (thinking, agent_done, chat_done)
                if 'event' in chunk:
                    continue

                # Extract response_id
                if 'response_id' in chunk:
                    response_id = chunk['response_id']
                    continue

                # Format: {"text": "..."} - RAG Studio format
                if 'text' in chunk:
                    full_response.append(chunk['text'])
                # Format: {"content": "..."}
                elif 'content' in chunk:
                    full_response.append(chunk['content'])
                # Format: {"delta": {"content": "..."}}
                elif 'delta' in chunk and isinstance(chunk['delta'], dict):
                    if 'content' in chunk['delta']:
                        full_response.append(chunk['delta']['content'])
                # Format: {"choices": [{"delta": {"content": "..."}}]}
                elif 'choices' in chunk and chunk['choices']:
                    choice = chunk['choices'][0]
                    if 'delta' in choice and 'content' in choice['delta']:
                        full_response.append(choice['delta']['content'])
                    elif 'text' in choice:
                        full_response.append(choice['text'])

                # Extract sources if present
                if 'sources' in chunk:
                    sources.extend(chunk['sources'])
                elif 'references' in chunk:
                    sources.extend(chunk['references'])
                elif 'source_nodes' in chunk:
                    sources.extend(chunk['source_nodes'])
        except json.JSONDecodeError:
            # If not JSON, treat as plain text
            full_response.append(line)

    return {
        "answer": "".join(full_response),
        "sources": sources,
        "response_id": response_id
    }


def run_tool(config: UserParameters, args: ToolParameters) -> str:
    """
    Main tool execution function.
    """
    try:
        base_url = config.base_url.rstrip('/')
        headers = _build_headers(config.api_key)
        timeout = config.timeout_seconds

        # Handle 'list_knowledge_bases' action
        if args.action == "list_knowledge_bases":
            return handle_list_knowledge_bases(base_url, headers, timeout)

        # Handle 'query' action
        elif args.action == "query":
            return handle_query(base_url, headers, timeout, config, args)

        # Handle 'get_sessions' action
        elif args.action == "get_sessions":
            return handle_get_sessions(base_url, headers, timeout)

        # Handle 'get_chat_history' action
        elif args.action == "get_chat_history":
            return handle_get_chat_history(base_url, headers, timeout, args)

        # Handle 'upload_document' action
        elif args.action == "upload_document":
            return handle_upload_document(base_url, headers, timeout, config, args)

        else:
            return f"Error: Unsupported action '{args.action}'."

    except requests.exceptions.RequestException as e:
        return f"RAG Studio request failed: {str(e)}"
    except Exception as e:
        return f"Tool execution failed: {str(e)}"


def handle_list_knowledge_bases(base_url: str, headers: Dict[str, str], timeout: int) -> str:
    """List all available knowledge bases (data sources)."""
    data_sources = get_data_sources(base_url, headers, timeout)

    if not data_sources:
        return "No knowledge bases found in RAG Studio."

    formatted = ["Available Knowledge Bases:\n"]
    for ds in data_sources:
        formatted.append(
            f"- Name: {ds.get('name', 'N/A')}\n"
            f"  ID: {ds.get('id', 'N/A')}\n"
            f"  Documents: {ds.get('documentCount', 0)}\n"
            f"  Embedding Model: {ds.get('embeddingModel', 'N/A')}\n"
        )

    return "\n".join(formatted)


def handle_query(base_url: str, headers: Dict[str, str],
                 timeout: int, config: UserParameters, args: ToolParameters) -> str:
    """Handle RAG query operation."""
    if not args.query:
        return "Error: 'query' parameter is required for 'query' action."

    # Get all data sources
    data_sources = get_data_sources(base_url, headers, timeout)

    # Find the target data source using the configured knowledge_base_name
    data_source = find_data_source_by_name(data_sources, config.knowledge_base_name)

    if not data_source:
        available = ", ".join([f"'{ds.get('name', 'Unknown')}'" for ds in data_sources])
        return f"Error: Knowledge base '{config.knowledge_base_name}' not found. Available knowledge bases: {available}"

    data_source_id = data_source.get('id')
    data_source_name = data_source.get('name')

    # Create a session for querying
    session_id = None
    try:
        session = create_session(
            base_url, headers,
            data_source_ids=[data_source_id],
            project_id=config.project_id,
            inference_model=config.inference_model,
            response_chunks=config.response_chunks,
            timeout=timeout
        )
        session_id = session.get('id')
    except requests.exceptions.RequestException as e:
        return f"Error creating query session: {str(e)}"

    # Send the query to the session
    try:
        chat_response = send_chat_message(
            base_url, headers, session_id, args.query, timeout
        )

        # Extract the response
        answer = chat_response.get("answer", "")
        sources = chat_response.get("sources", [])

        if not answer:
            answer = "(No response received)"

        # Format the result
        result_parts = [f"Knowledge Base: {data_source_name}", f"Answer: {answer}"]

        if sources:
            result_parts.append("\nSources:")
            for source in sources:
                if isinstance(source, str):
                    result_parts.append(f"  - {source}")
                elif isinstance(source, dict):
                    name = source.get('name') or source.get('title') or source.get('filename', 'Unknown')
                    result_parts.append(f"  - {name}")

        return "\n".join(result_parts)

    except requests.exceptions.RequestException as e:
        return f"Error querying RAG system: {str(e)}"
    finally:
        # Clean up session
        if session_id:
            delete_session(base_url, headers, session_id, timeout)


def handle_get_sessions(base_url: str, headers: Dict[str, str], timeout: int) -> str:
    """List all available sessions."""
    sessions = get_sessions(base_url, headers, timeout)

    if not sessions:
        return "No sessions found in RAG Studio."

    formatted = ["Available Sessions:\n"]
    for session in sessions:
        formatted.append(
            f"- ID: {session.get('id', 'N/A')}\n"
            f"  Name: {session.get('name', 'N/A')}\n"
            f"  Data Sources: {session.get('dataSourceIds', [])}\n"
            f"  Inference Model: {session.get('inferenceModel', 'N/A')}\n"
        )

    return "\n".join(formatted)


def handle_get_chat_history(base_url: str, headers: Dict[str, str],
                            timeout: int, args: ToolParameters) -> str:
    """Get chat history with evaluations for a session."""
    if not args.session_id:
        return "Error: 'session_id' parameter is required for 'get_chat_history' action."

    history = get_chat_history(base_url, headers, args.session_id, timeout)

    if not history or not history.get('data'):
        return f"No chat history found for session {args.session_id}."

    formatted = [f"Chat History for Session {args.session_id}:\n"]

    for entry in history.get('data', []):
        rag_message = entry.get('rag_message', {})
        evaluations = entry.get('evaluations', [])
        source_nodes = entry.get('source_nodes', [])

        formatted.append(f"--- Message ID: {entry.get('id', 'N/A')} ---")
        formatted.append(f"User: {rag_message.get('user', 'N/A')}")
        formatted.append(f"Assistant: {rag_message.get('assistant', 'N/A')[:500]}...")

        if evaluations:
            formatted.append("Evaluations:")
            for eval_item in evaluations:
                name = eval_item.get('name', 'unknown')
                value = eval_item.get('value', 'N/A')
                formatted.append(f"  - {name}: {value}")

        if source_nodes:
            formatted.append(f"Sources: {len(source_nodes)} documents retrieved")

        formatted.append("")

    return "\n".join(formatted)


def handle_upload_document(base_url: str, headers: Dict[str, str],
                           timeout: int, config: UserParameters,
                           args: ToolParameters) -> str:
    """Handle document upload to a knowledge base."""
    import os

    if not args.file_path:
        return "Error: 'file_path' parameter is required for 'upload_document' action."

    if not os.path.exists(args.file_path):
        return f"Error: File not found: {args.file_path}"

    # Get all data sources to find the target knowledge base
    data_sources = get_data_sources(base_url, headers, timeout)

    # Find the target data source using the configured knowledge_base_name
    data_source = find_data_source_by_name(data_sources, config.knowledge_base_name)

    if not data_source:
        available = ", ".join([f"'{ds.get('name', 'Unknown')}'" for ds in data_sources])
        return f"Error: Knowledge base '{config.knowledge_base_name}' not found. Available: {available}"

    data_source_id = data_source.get('id')
    data_source_name = data_source.get('name')

    try:
        result = upload_document(
            base_url, config.api_key, data_source_id,
            args.file_path, timeout
        )

        filename = os.path.basename(args.file_path)
        return (
            f"Document uploaded successfully!\n"
            f"  File: {filename}\n"
            f"  Knowledge Base: {data_source_name} (ID: {data_source_id})\n"
            f"  Response: {result}"
        )

    except requests.exceptions.RequestException as e:
        return f"Error uploading document: {str(e)}"


OUTPUT_KEY = "tool_output"


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--user-params", required=True, help="JSON string for tool configuration")
    parser.add_argument("--tool-params", required=True, help="JSON string for tool arguments")
    cli_args = parser.parse_args()

    config_dict = json.loads(cli_args.user_params)
    params_dict = json.loads(cli_args.tool_params)

    config = UserParameters(**config_dict)
    params = ToolParameters(**params_dict)

    output = run_tool(config, params)
    print(OUTPUT_KEY, output)
