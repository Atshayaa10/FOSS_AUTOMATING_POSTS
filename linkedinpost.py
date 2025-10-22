# linkedin_post.py
import requests
import json
import sys
import os
ACCESS_TOKEN=''
# ========= CONFIG: replace these with your app values ================
CLIENT_ID = ""
CLIENT_SECRET = ""
# This must exactly match the redirect URI you registered in LinkedIn app settings
REDIRECT_URI = "http://localhost:3003/auth/linkedin/callback"

# If you already have an access token you can paste it here and skip the exchange step:

# e.g. "AQX...replace_with_real_token"

# LinkedIn-Version header (format YYYYMM). Use a recent YYYYMM (I used current month).
LINKEDIN_VERSION = "202510"   # format: YYYYMM (update if needed)

# =============== Helpers =================================================
def exchange_code_for_access_token(code):
    """
    Exchange an authorization code for an access token.
    Docs: Authorization Code Flow / accessToken endpoint.
    """
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
    return r.json()   # contains access_token, expires_in, maybe refresh_token

def get_my_profile(access_token):
    import json
    url = "https://api.linkedin.com/v2/me"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "X-Restli-Protocol-Version": "2.0.0",
        "Accept": "application/json"
    }
    try:
        r = requests.get(url, headers=headers, timeout=30)
    except requests.RequestException as e:
        print("NETWORK ERROR calling /v2/me:", e)
        return None

    print("GET /v2/me status:", r.status_code)
    for h in ("x-restli-id", "linkedin-version", "retry-after", "www-authenticate"):
        if h in r.headers:
            print(f"Response header {h}: {r.headers[h]}")
    # Print body (JSON if possible)
    try:
        pretty = json.dumps(r.json(), indent=2)
        print("Response JSON:\n", pretty)
    except Exception:
        print("Response text:", r.text[:2000])  # truncate
    if r.status_code >= 400:
        print("LinkedIn returned an error for /v2/me. See above.")
        return None
    return r.json()

def create_text_post(access_token, author_urn, text, visibility="PUBLIC"):
    """
    Create a text-only post using the Posts API:
    POST https://api.linkedin.com/rest/posts
    Required headers shown in LinkedIn docs.
    """
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

# =============== Main flow ==============================================
def main():
    global ACCESS_TOKEN
    if ACCESS_TOKEN is None:
        # If you were redirected back from LinkedIn to your redirect URI with ?code=..., paste it here:
        if len(sys.argv) < 2:
            print("No ACCESS_TOKEN set and no auth code provided.")
            print("Usage: python linkedin_post.py AUTHORIZATION_CODE")
            sys.exit(1)
        auth_code = sys.argv[1].strip()
        print("Exchanging authorization code for access token...")
        token_resp = exchange_code_for_access_token(auth_code)
        ACCESS_TOKEN = token_resp.get("access_token")
        print("Got access_token (expires_in = {})".format(token_resp.get("expires_in")))

    # 1) Get current user profile to build the author URN
    profile = get_my_profile(ACCESS_TOKEN)
    if not profile:
        print("ERROR: could not fetch profile. The get_my_profile(...) function printed debug info above.")
        print("Common causes: invalid/expired token, missing scopes (r_liteprofile), or wrong Authorization header.")
    sys.exit(1)

    author_urn = f"urn:li:person:{member_id}"
    print("Will post as:", author_urn)

    # 2) Create a dummy text post
    text = "Hello from the API — test post (dummy)."
    print("Creating text post...")
    resp = create_text_post(ACCESS_TOKEN, author_urn, text, visibility="PUBLIC")

    if resp.status_code in (200, 201):
        post_id = resp.headers.get("x-restli-id") or resp.json().get("id")
        print("Post created! post id:", post_id)
        print("Response body:", resp.text)
    else:
        print("Failed to create post. Status:", resp.status_code)
        print("Response headers:", resp.headers)
        try:
            print("Response body:", resp.json())
        except Exception:
            print("Response text:", resp.text)
        sys.exit(1)

if __name__ == "__main__":
    main()
 

