from azure.identity import ClientSecretCredential
from msgraph.graph_service_client import GraphServiceClient


def test_graph_client_and_entra_credential_are_available() -> None:
    assert callable(GraphServiceClient)
    assert callable(ClientSecretCredential)
