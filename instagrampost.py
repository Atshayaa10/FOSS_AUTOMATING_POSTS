## Instagram Post Automation Script

python
# instagram_post.py
import requests
import json
import sys
import os
from datetime import datetime

# ========= CONFIG: replace these with your app values ================
ACCESS_TOKEN = ''
CLIENT_ID = ""
CLIENT_SECRET = ""
REDIRECT_URI = "https://localhost:3003/auth/instagram/callback"  # Must match app settings

# Instagram Graph API version
INSTAGRAM_API_VERSION = "v19.0"  # Use latest available version

# =============== Helpers =================================================
def exchange_code_for_access_token(code):
    """
    Exchange an authorization code for an access token.
    Instagram Graph API OAuth flow.
    """
    url = "https://api.instagram.com/oauth/access_token"
    data = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "grant_type": "authorization_code",
        "redirect_uri": REDIRECT_URI,
        "code": code
    }
    
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    r = requests.post(url, data=data, headers=headers, timeout=30)
    r.raise_for_status()
    return r.json()

def get_long_lived_token(short_lived_token):
    """
    Exchange short-lived token for long-lived token (60 days).
    """
    url = "https://graph.instagram.com/access_token"
    params = {
        "grant_type": "ig_exchange_token",
        "client_secret": CLIENT_SECRET,
        "access_token": short_lived_token
    }
    
    r = requests.get(url, params=params, timeout=30)
    r.raise_for_status()
    return r.json()

def refresh_long_lived_token(long_lived_token):
    """
    Refresh long-lived token before it expires.
    """
    url = "https://graph.instagram.com/refresh_access_token"
    params = {
        "grant_type": "ig_refresh_token",
        "access_token": long_lived_token
    }
    
    r = requests.get(url, params=params, timeout=30)
    r.raise_for_status()
    return r.json()

def get_instagram_business_account(access_token):
    """
    Get Instagram Business Account ID linked to Facebook Page.
    Requires Facebook Page access and connected Instagram account.
    """
    # First get user's pages
    url = f"https://graph.facebook.com/{INSTAGRAM_API_VERSION}/me/accounts"
    params = {
        "access_token": access_token,
        "fields": "id,name,access_token,instagram_business_account"
    }
    
    r = requests.get(url, params=params, timeout=30)
    r.raise_for_status()
    
    pages_data = r.json()
    
    if "data" not in pages_data or not pages_data["data"]:
        print("No Facebook Pages found. You need a Facebook Page connected to Instagram Business Account.")
        return None
    
    # Find page with Instagram business account
    for page in pages_data["data"]:
        if "instagram_business_account" in page:
            ig_account = page["instagram_business_account"]
            print(f"Found Instagram Business Account: {ig_account}")
            return ig_account["id"], page["access_token"]
    
    print("No Instagram Business Account found connected to your Facebook Pages.")
    return None

def get_instagram_user_profile(access_token, ig_user_id):
    """
    Get Instagram user profile information.
    """
    url = f"https://graph.instagram.com/{INSTAGRAM_API_VERSION}/{ig_user_id}"
    params = {
        "access_token": access_token,
        "fields": "id,username,account_type,media_count,profile_picture_url"
    }
    
    r = requests.get(url, params=params, timeout=30)
    r.raise_for_status()
    return r.json()

def create_instagram_post(access_token, ig_user_id, caption, image_url=None):
    """
    Create an Instagram post.
    For image posts, you need to go through container creation process.
    """
    
    if image_url:
        # Step 1: Create media container
        container_url = f"https://graph.facebook.com/{INSTAGRAM_API_VERSION}/{ig_user_id}/media"
        container_data = {
            "access_token": access_token,
            "caption": caption,
            "image_url": image_url  # Publicly accessible URL
        }
        
        print("Creating media container...")
        container_response = requests.post(container_url, data=container_data, timeout=30)
        container_response.raise_for_status()
        
        creation_id = container_response.json().get("id")
        print(f"Media container created with ID: {creation_id}")
        
        # Step 2: Publish the container
        publish_url = f"https://graph.facebook.com/{INSTAGRAM_API_VERSION}/{ig_user_id}/media_publish"
        publish_data = {
            "access_token": access_token,
            "creation_id": creation_id
        }
        
        print("Publishing media...")
        publish_response = requests.post(publish_url, data=publish_data, timeout=30)
        publish_response.raise_for_status()
        
        return publish_response.json()
    
    else:
        # For carousel posts or other types, you'd extend this
        print("Currently only image posts with URLs are implemented.")
        return None

def create_instagram_story(access_token, ig_user_id, image_url, caption=None):
    """
    Create an Instagram story.
    Similar process to posts but with story-specific parameters.
    """
    # Create story container
    container_url = f"https://graph.facebook.com/{INSTAGRAM_API_VERSION}/{ig_user_id}/media"
    container_data = {
        "access_token": access_token,
        "media_type": "STORIES",
        "image_url": image_url,
        "caption": caption or ""
    }
    
    print("Creating story container...")
    container_response = requests.post(container_url, data=container_data, timeout=30)
    container_response.raise_for_status()
    
    creation_id = container_response.json().get("id")
    print(f"Story container created with ID: {creation_id}")
    
    # Publish story
    publish_url = f"https://graph.facebook.com/{INSTAGRAM_API_VERSION}/{ig_user_id}/media_publish"
    publish_data = {
        "access_token": access_token,
        "creation_id": creation_id
    }
    
    print("Publishing story...")
    publish_response = requests.post(publish_url, data=publish_data, timeout=30)
    publish_response.raise_for_status()
    
    return publish_response.json()

def get_media_insights(access_token, media_id):
    """
    Get insights for a specific media post.
    """
    url = f"https://graph.facebook.com/{INSTAGRAM_API_VERSION}/{media_id}/insights"
    params = {
        "access_token": access_token,
        "metric": "engagement,impressions,reach,saved"
    }
    
    r = requests.get(url, params=params, timeout=30)
    r.raise_for_status()
    return r.json()

# =============== Main flow ==============================================
def main():
    global ACCESS_TOKEN
    
    if not ACCESS_TOKEN:
        if len(sys.argv) < 2:
            print("No ACCESS_TOKEN set and no auth code provided.")
            print("Usage: python instagram_post.py AUTHORIZATION_CODE [IMAGE_URL]")
            print("\nNote: You need:")
            print("- Instagram Business Account")
            print("- Facebook Page connected to Instagram")
            print("- App with instagram_basic, instagram_content_publish, pages_read_engagement permissions")
            sys.exit(1)
        
        auth_code = sys.argv[1].strip()
        print("Exchanging authorization code for access token...")
        
        try:
            token_resp = exchange_code_for_access_token(auth_code)
            short_lived_token = token_resp.get("access_token")
            user_id = token_resp.get("user_id")
            
            print("Got short-lived access token")
            print("Getting long-lived token...")
            
            long_lived_resp = get_long_lived_token(short_lived_token)
            ACCESS_TOKEN = long_lived_resp.get("access_token")
            expires_in = long_lived_resp.get("expires_in")
            
            print(f"Got long-lived token (expires in: {expires_in} seconds)")
            
        except requests.RequestException as e:
            print(f"Error during token exchange: {e}")
            sys.exit(1)

    # Get Instagram Business Account
    print("Getting Instagram Business Account...")
    ig_account_info = get_instagram_business_account(ACCESS_TOKEN)
    
    if not ig_account_info:
        print("Failed to get Instagram Business Account.")
        sys.exit(1)
    
    ig_user_id, page_access_token = ig_account_info
    
    # Get profile info
    try:
        profile = get_instagram_user_profile(page_access_token, ig_user_id)
        print(f"Instagram Account: {profile.get('username')} (ID: {profile.get('id')})")
    except requests.RequestException as e:
        print(f"Error getting profile: {e}")
        sys.exit(1)

    # Create post
    caption = "Hello from Instagram Graph API! 🤖 #automation #api"
    
    # Check if image URL provided
    image_url = sys.argv[2] if len(sys.argv) > 2 else None
    
    try:
        if image_url:
            print(f"Creating post with image: {image_url}")
            post_result = create_instagram_post(page_access_token, ig_user_id, caption, image_url)
        else:
            print("No image URL provided. Creating post with default image...")
            # You might want to use a default image or implement carousel/text posts
            post_result = create_instagram_post(page_access_token, ig_user_id, caption, "https://via.placeholder.com/1080x1080.png")
        
        if post_result:
            media_id = post_result.get("id")
            print(f"Post created successfully! Media ID: {media_id}")
            
            # Get insights after a short delay
            import time
            time.sleep(5)  # Wait for processing
            
            try:
                insights = get_media_insights(page_access_token, media_id)
                print("Post insights:", json.dumps(insights, indent=2))
            except requests.RequestException as e:
                print(f"Could not get insights yet: {e}")
        
    except requests.RequestException as e:
        print(f"Error creating post: {e}")
        if hasattr(e, 'response') and e.response:
            print(f"Response: {e.response.text}")
        sys.exit(1)

if __name__ == "__main__":
    main()


