import requests
import logging
from ..config import Config

logger = logging.getLogger(__name__)

def create_tenant_for_user(user_id: int, username: str, email: str) -> int:
    """
    Create a tenant in agentic-saas-backend and return the tenant_id
    
    Args:
        user_id: The user ID from mino-ai
        username: The username
        email: The user's email
    
    Returns:
        tenant_id: The created tenant ID
    
    Raises:
        Exception: If tenant creation fails
    """
    tenant_api_url = Config.TENANT_API_URL
    if not tenant_api_url:
        logger.error("TENANT_API_URL not configured")
        raise ValueError("TENANT_API_URL not configured")
    
    # Create tenant name from username or email
    tenant_name = username or email.split('@')[0]
    
    # Prepare tenant creation payload
    payload = {
        "name": tenant_name,
        "domain": email.split('@')[1] if '@' in email else None,
        "plan": "free"
    }
    
    try:
        url = f"{tenant_api_url}/tenants/"
        logger.info(f"Creating tenant for user {user_id} at {url}")
        logger.info(f"Tenant payload: {payload}")
        
        response = requests.post(
            url,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        if response.status_code == 201:
            tenant_data = response.json()
            tenant_id = tenant_data.get('tenant_id')
            logger.info(f"Tenant created successfully: tenant_id={tenant_id} for user_id={user_id}")
            return tenant_id
        else:
            error_msg = f"Failed to create tenant: {response.status_code} - {response.text}"
            logger.error(error_msg)
            raise Exception(error_msg)
            
    except requests.exceptions.RequestException as e:
        logger.error(f"Error calling tenant API: {str(e)}")
        raise Exception(f"Failed to create tenant: {str(e)}")

