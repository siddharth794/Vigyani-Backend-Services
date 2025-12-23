import requests
import logging
from requests.exceptions import RequestException, ConnectionError, Timeout

logger = logging.getLogger(__name__)

AGENTIC_BASE_URL = "http://127.0.0.1:8000/tenants"


def sync_update_tenant(tenant_id, name=None, domain=None, plan=None):
    payload = {}

    if name:
        payload['name'] = name
    if domain:
        payload['domain'] = domain
    if plan:
        payload['plan'] = plan

    session = None
    try:
        url = f"{AGENTIC_BASE_URL}/{tenant_id}"
        # Use a session with proper connection handling
        session = requests.Session()
        response = session.put(url, json=payload, timeout=5)

        if response.status_code == 200:
            return True
        else:
            logger.error(f"Failed to sync tenant update: {response.text}")
            return False
    except (ConnectionError, Timeout) as e:
        logger.warning(f"Connection error syncing tenant update (tenant_id={tenant_id}): {str(e)}")
        return False
    except RequestException as e:
        logger.error(f"Request error syncing tenant update (tenant_id={tenant_id}): {str(e)}")
        return False
    except AttributeError as e:
        # Catch AttributeError which includes 'NoneType' object has no attribute 'settimeout'
        logger.warning(f"Connection attribute error syncing tenant update (tenant_id={tenant_id}): {str(e)}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error syncing tenant update (tenant_id={tenant_id}): {str(e)}")
        return False
    finally:
        # Ensure session is closed
        if session is not None:
            try:
                session.close()
            except:
                pass
