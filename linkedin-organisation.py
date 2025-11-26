import requests
import json
import sys
import os
from dotenv import load_dotenv
load_dotenv()
# =====================================================================
# Fetch secrets from environment variables
ACCESS_TOKEN = os.environ.get("LINKEDIN_ACCESS_TOKEN", "")
CLIENT_ID = os.environ.get("LINKEDIN_CLIENT_ID")
CLIENT_SECRET = os.environ.get("LINKEDIN_CLIENT_SECRET")
REDIRECT_URI = os.environ.get("LINKEDIN_REDIRECT_URI", "http://localhost:3003/auth/linkedin/callback")

LINKEDIN_VERSION = "202510"   # YYYYMM

# =====================================================================
def get_authorization_url():
    """Generate the LinkedIn OAuth authorization URL with required scopes"""
    scopes = ["openid", "profile", "w_organization_social"]
    scope_string = "%20".join(scopes)
    
    auth_url = (
        f"https://www.linkedin.com/oauth/v2/authorization"
        f"?response_type=code"
        f"&client_id={CLIENT_ID}"
        f"&redirect_uri={REDIRECT_URI}"
        f"&scope={scope_string}"
    )
    return auth_url


def exchange_code_for_access_token(code):
    """Exchange authorization code for access token"""
    url = "https://www.linkedin.com/oauth/v2/accessToken"
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    r = requests.post(url, data=data, headers=headers, timeout=30)
    r.raise_for_status()
    return r.json()

def get_organization_pages(access_token):
    url = "https://api.linkedin.com/v2/organizationalEntityAcls"
    headers = {"Authorization": f"Bearer {access_token}"}
    params = {
        "q": "roleAssignee",
        "role": "ADMINISTRATOR",
        "state": "APPROVED"
    }
    r = requests.get(url, headers=headers, params=params)
    r.raise_for_status()
    return r.json()


def get_my_profile(access_token):
    """Get user profile using OpenID Connect userinfo endpoint"""
    url = "https://api.linkedin.com/v2/userinfo"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json"
    }

    r = requests.get(url, headers=headers, timeout=30)
    print("GET /v2/userinfo status:", r.status_code)

    try:
        parsed = r.json()
        print(json.dumps(parsed, indent=2))
    except:
        print("Response text:", r.text)

    if r.status_code >= 400:
        print("LinkedIn userinfo error.")
        return None

    sub = parsed.get("sub")
    if sub:
        parsed["id"] = sub
    
    return parsed


def create_text_post(access_token, author_urn, text, visibility="PUBLIC"):
    """Create a text post on LinkedIn"""
    url = "https://api.linkedin.com/rest/posts"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "X-Restli-Protocol-Version": "2.0.0",
        "LinkedIn-Version": LINKEDIN_VERSION,
        "Content-Type": "application/json"
    }
    payload = {
        "author": author_urn,
        "commentary": text,
        "visibility": visibility,
        "distribution": {
            "feedDistribution": "MAIN_FEED",
            "targetEntities": [],
            "thirdPartyDistributionChannels": []
        },
        "lifecycleState": "PUBLISHED",
        "isReshareDisabledByAuthor": False
    }

    r = requests.post(url, headers=headers, json=payload, timeout=30)
    return r


# =====================================================================
def main():
    global ACCESS_TOKEN

    # Ensure required environment variables are set
    if not CLIENT_ID or not CLIENT_SECRET:
        print("✗ Please set LINKEDIN_CLIENT_ID and LINKEDIN_CLIENT_SECRET in your environment.")
        sys.exit(1)

    # 0) Show authorization URL if access token not provided
    if not ACCESS_TOKEN and len(sys.argv) < 2:
        print("=" * 60)
        print("LINKEDIN OAUTH SETUP")
        print("=" * 60)
        print("\nSTEP 1: Visit this authorization URL in your browser:\n")
        print(get_authorization_url())
        print("\nSTEP 2: After authorizing, you'll be redirected to:")
        print(f"        {REDIRECT_URI}?code=YOUR_AUTH_CODE&state=...")
        print("\nSTEP 3: Copy the 'code' parameter and run:")
        print("        python linkedin_post.py YOUR_AUTH_CODE")
        print("\n" + "=" * 60)
        sys.exit(0)

    # 1) Exchange code for access token if needed
    if not ACCESS_TOKEN:
        auth_code = sys.argv[1].strip()
        print("Exchanging authorization code for access token…")
        try:
            token_resp = exchange_code_for_access_token(auth_code)
            ACCESS_TOKEN = token_resp.get("access_token")
            print("✓ Access Token obtained:", ACCESS_TOKEN[:20] + "...")
            print("✓ Expires in:", token_resp.get("expires_in"), "seconds")
        except requests.exceptions.HTTPError as e:
            print("✗ Error exchanging code:", e)
            print("Response:", e.response.text if hasattr(e, 'response') else '')
            sys.exit(1)

    # 2) Get profile
    print("Fetching profile…")
    profile = get_my_profile(ACCESS_TOKEN)
    if not profile:
        print("✗ Failed to fetch profile.")
        sys.exit(1)

    member_id = profile.get("id")
    if not member_id:
        print("✗ Profile JSON does not contain 'id' or 'sub'.")
        print("Profile data:", profile)
        sys.exit(1)

    author_urn = "urn:li:organization:12345678"  # replace with your org ID
    print(f"✓ Posting as: {author_urn}\n")

    # 3) Create a post
    text = "Hey, This is Raj! Just unit testing the automated functionality for LinkedIn posts for organisation page."
    print("Creating post…")

    resp = create_text_post(ACCESS_TOKEN, author_urn, text)

    if resp.status_code in (200, 201):
        print("✓ Post created successfully!")
        try:
            print("Response:", json.dumps(resp.json(), indent=2))
        except:
            print("Response:", resp.text)
    else:
        print(f"✗ Failed to create post: {resp.status_code}")
        try:
            print("Body:", json.dumps(resp.json(), indent=2))
        except:
            print("Body:", resp.text)
        sys.exit(1)


if __name__ == "__main__":
    main()
