import logging
import boto3
from botocore.exceptions import ClientError


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

def complete_chat(prompt,
                          model_id="anthropic.claude-3-5-sonnet-20240620-v1:0",
                          system_prompt="You are a helpful assistant", 
                          ):
    """
    Sends messages to a model.
    Args:
        bedrock_client: The Boto3 Bedrock runtime client.
        model_id (str): The model ID to use.
        system_prompts (JSON) : The system prompts for the model to use.
        messages (JSON) : The messages to send to the model.

    Returns:
        response (JSON): The conversation that the model generated.

    """

    bedrock_client = boto3.client(service_name='bedrock-runtime', 
                             region_name='us-west-2', 
                             aws_access_key_id=st.secrets["AWS_ACCESS_KEY_ID"],
                             aws_secret_access_key=st.secrets["AWS_SECRET_ACCESS_KEY"])
    
    logger.info("Generating message with model %s", model_id)

    # Inference parameters to use.
    temperature = 0.0
    top_k = 1

    # Base inference parameters to use.
    inference_config = {"temperature": temperature}
    # Additional inference parameters to use.
    additional_model_fields = {"top_k": top_k}

    messages = [{
        "role": "user",
        "content": [{"text": prompt}]}]
    system_prompts = [{"text": system_prompt}]

    # Send the message.
    response = bedrock_client.converse(
        modelId=model_id,
        messages=messages,
        system=system_prompts,
        inferenceConfig=inference_config,
        additionalModelRequestFields=additional_model_fields
    )

    # Log token usage.
    token_usage = response['usage']
    logger.info("Input tokens: %s", token_usage['inputTokens'])
    logger.info("Output tokens: %s", token_usage['outputTokens'])
    logger.info("Total tokens: %s", token_usage['totalTokens'])
    logger.info("Stop reason: %s", response['stopReason'])

    return response["output"]["message"]["content"][0]["text"]