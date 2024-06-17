import base64
import boto3


# eu-central-1 for Frankfurt
def get_secret(name: str, region_name: str = "eu-west-1") -> str:
    # Create a Secrets Manager client
    client = boto3.client("secretsmanager", region_name=region_name)

    try:
        # Retrieve the secret value
        get_secret_value_response = client.get_secret_value(SecretId=name)

        # Secrets Manager decrypts the secret value using the associated KMS key
        if "SecretString" in get_secret_value_response:
            secret = get_secret_value_response["SecretString"]
        else:
            secret = base64.b64decode(get_secret_value_response["SecretBinary"]).decode(
                "utf-8"
            )

        return secret

    except Exception as e:
        raise RuntimeError(f"Error retrieving secret: {e}")
