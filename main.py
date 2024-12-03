from pathlib import Path
from openai import OpenAI

def read_from_file(file_path):
    with open(file_path, 'r') as file:
        return file.read().strip()

def get_api_keys():
    api_key = read_from_file(Path('keys/openAi_key.txt').resolve())
    organization_id = read_from_file(Path('keys/openAi_organization_id.txt').resolve())
    project_id = read_from_file(Path('keys/openAi_project_id.txt').resolve())
    return api_key, organization_id, project_id

def create_client(api_key, organization_id, project_id):
    return OpenAI(
        api_key=api_key,
        organization=organization_id,
        project=project_id,
    )

def check_assistant_exists(client, assistant_name):
    existing_assistants = client.beta.assistants.list()
    assistants_list = existing_assistants.data if hasattr(existing_assistants, 'data') else []
    return any(assistant.name == assistant_name for assistant in assistants_list)

def create_assistant(client, assistant_name):
    return client.beta.assistants.create(
        name=assistant_name,
        instructions="You are an expert in querying and analyzing a database stored in memory. Use your knowledge and the file_search tool to perform various SELECT queries and operations based on provided IDs and other criteria.",
        model="gpt-4o",
        tools=[{"type": "file_search"}],
    )

def get_vector_store(client, vector_store_name):
    existing_vector_stores = client.beta.vector_stores.list()
    vector_store_exists = any(vector_store.name == vector_store_name for vector_store in existing_vector_stores)
    
    if vector_store_exists:
        return next((vs for vs in existing_vector_stores if vs.name == vector_store_name), None)
    return None

def create_vector_store(client, vector_store_name):
    vector_store = client.beta.vector_stores.create(name=vector_store_name)
    print(f"Vector store '{vector_store_name}' created with ID: {vector_store.id}")
    
    file_paths = ["siruta_rez.txt"]
    file_streams = [open(path, "rb") for path in file_paths]
    
    file_batch = client.beta.vector_stores.file_batches.upload_and_poll(
        vector_store_id=vector_store.id, files=file_streams
    )
    
    print(file_batch.status)
    print(file_batch.file_counts)
    
    return vector_store

def update_assistant_with_vector_store(client, assistant, vector_store):
    tool_resources = assistant.tool_resources
    file_search_tool = next(
        (tool for tool in tool_resources if hasattr(tool, 'type') and tool.type == "file_search"), 
        None
    )
    
    if file_search_tool:
        vector_store_ids = getattr(file_search_tool, 'vector_store_ids', [])
        if vector_store.id not in vector_store_ids:
            updated_assistant = client.beta.assistants.update(
                assistant_id=assistant.id,
                tool_resources={"file_search": {"vector_store_ids": vector_store_ids + [vector_store.id]}}
            )
            print("\nAssistant updated successfully.")
        else:
            print(f"\nThe assistant already has the vector store ID {vector_store.id} in its tool resources.")
    else:
        updated_assistant = client.beta.assistants.update(
            assistant_id=assistant.id,
            tool_resources={"file_search": {"vector_store_ids": [vector_store.id]}}
        )
        print("\nAssistant updated with new file_search tool resources.")

def create_and_poll_thread(client, assistant, vector_store_id, query_content, file_id):
    try:
        thread = client.beta.threads.create(
            messages=[{
                "role": "user",
                "content": query_content,
                "attachments": [
                    {"file_id": file_id, "tools": [{"type": "file_search"}]}
                ]
            }]
        )
        print("Query thread created successfully.")
        return thread
    except Exception as e:
        print(f"An error occurred while creating the thread: {e}")
        return None

def wait_for_assistant_response(client, thread, assistant):
    try:
        run = client.beta.threads.runs.create_and_poll(
            thread_id=thread.id, assistant_id=assistant.id
        )
        
        messages = list(client.beta.threads.messages.list(thread_id=thread.id, run_id=run.id))
        
        if not messages:
            print("No messages found in the thread.")
        else:
            message_content = messages[0].content[0].text
            
            annotations = message_content.annotations
            citations = []
            for index, annotation in enumerate(annotations):
                message_content.value = message_content.value.replace(annotation.text, f"[{index}]")
                if file_citation := getattr(annotation, "file_citation", None):
                    cited_file = client.files.retrieve(file_citation.file_id)
                    citations.append(f"[{index}] {cited_file.filename}")

            print("\nMessage:\n", message_content.value)
            print("\n".join(citations))
    except Exception as e:
        print(f"An error occurred while waiting for the assistant's response: {e}")


def main():
    api_key, organization_id, project_id = get_api_keys()
    client = create_client(api_key, organization_id, project_id)
    
    assistant_name = "Database Query Assistant"
    
    if not check_assistant_exists(client, assistant_name):
        assistant = create_assistant(client, assistant_name)
    else:
        print(f"An assistant with the name '{assistant_name}' already exists.")
        existing_assistants = client.beta.assistants.list()
        assistant = next(assistant for assistant in existing_assistants.data if assistant.name == assistant_name)

    vector_store_name = "Siruta Database"
    
    vector_store = get_vector_store(client, vector_store_name)

    if vector_store is None:
        vector_store = create_vector_store(client, vector_store_name)

    fileId = None
    files = client.beta.vector_stores.files.list(vector_store_id=vector_store.id)
    for file in files:
        print(f"File ID: {file.id}")
        fileId = file.id

    
    update_assistant_with_vector_store(client, assistant, vector_store)
    
    sir_sup_code = "1017"
    #sir_sup_code = "2130"
    #sir_sup_code = "9999"   # Invalid code
    query_content = f"Retrieve the 'DENLOC' value from the file siruta_rez.txt located in the vector storage of the attached 'Siruta Database', where the 'DENLOC' field corresponds to the record in which the 'SIRUTA' field is equal to the provided 'SIRSUP' code '{sir_sup_code}'. If no matching 'SIRSUP' code is found, return a JSON object with the message 'No matching record found for SIRSUP code {sir_sup_code}'. Do not include any additional text or explanations outside the JSON object."
    thread = create_and_poll_thread(client, assistant, vector_store.id, query_content, file_id=fileId)
    
    if thread:
        wait_for_assistant_response(client, thread, assistant)

if __name__ == "__main__":
    main()
