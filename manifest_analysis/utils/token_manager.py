"""
GitHub Token Manager - Reusable Token Rotation Module

This module provides a TokenManager class that automatically rotates through
multiple GitHub Personal Access Tokens when one fails due to rate limiting or
authentication issues.

Usage:
    from manifest_analysis.utils.token_manager import token_manager
    
    # Get headers for API requests
    headers = token_manager.get_headers()
    
    # Make request (automatic rotation handled internally)
    response = requests.get(url, headers=headers)

The TokenManager automatically loads tokens from 'tokens.txt' in the project root.
"""

import os
import time


class TokenManager:
    """Manages multiple GitHub tokens with automatic rotation on failure."""
    
    def __init__(self, token_file='tokens.txt'):
        """
        Load all tokens from the token file.
        
        Args:
            token_file: Path to the file containing tokens (one per line)
        """
        self.tokens = []
        self.current_token_index = 0
        self._load_tokens(token_file)
    
    def _load_tokens(self, token_file):
        """Load tokens from file, trying multiple possible locations."""
        possible_paths = [
            token_file,  # Direct path
            os.path.join(os.path.dirname(__file__), token_file),  # Same directory
            os.path.join(os.path.dirname(__file__), '..', token_file),  # Parent directory
            os.path.join(os.path.dirname(os.path.dirname(__file__)), token_file),  # Two levels up
        ]
        
        for path in possible_paths:
            try:
                with open(path, 'r') as f:
                    self.tokens = [line.strip() for line in f if line.strip()]
                
                if self.tokens:
                    print(f"✓ Loaded {len(self.tokens)} token(s) from {path}")
                    return
            except FileNotFoundError:
                continue
        
        # If we get here, no token file was found
        print(f"⚠️  Warning: Token file '{token_file}' not found in any expected location.")
        print("   Tried paths:")
        for path in possible_paths:
            print(f"   - {path}")
        
        # Fallback to environment variable
        env_token = os.environ.get('GITHUB_TOKEN')
        if env_token:
            self.tokens = [env_token]
            print(f"✓ Using token from GITHUB_TOKEN environment variable")
        else:
            print("✗ No tokens available. GitHub API requests may fail.")
    
    def get_current_token(self):
        """Returns the current active token."""
        if not self.tokens:
            return None
        return self.tokens[self.current_token_index]
    
    def get_headers(self):
        """Returns headers with the current token."""
        token = self.get_current_token()
        if token:
            return {"Authorization": f"token {token}"}
        return {}
    
    def rotate_token(self):
        """
        Rotates to the next token in the list.
        
        Returns:
            bool: True if rotation was successful, False if we've cycled through all tokens
        """
        if not self.tokens or len(self.tokens) == 1:
            return False
        
        old_index = self.current_token_index
        self.current_token_index = (self.current_token_index + 1) % len(self.tokens)
        print(f"🔄 Rotating token: {old_index + 1} → {self.current_token_index + 1} of {len(self.tokens)}")
        return self.current_token_index != old_index
    
    def has_more_tokens(self):
        """Checks if there are more tokens to try (haven't cycled through all)."""
        return len(self.tokens) > 1
    
    def get_token_count(self):
        """Returns the total number of tokens available."""
        return len(self.tokens)


# Global instance for easy import and use
token_manager = TokenManager()


def fetch_with_token_rotation(url, session=None, max_retries=3, timeout=10):
    """
    Fetch URL with automatic token rotation on failure.
    
    Args:
        url: URL to fetch
        session: Optional requests.Session object
        max_retries: Maximum retry attempts
        timeout: Request timeout in seconds
    
    Returns:
        requests.Response object or None on failure
    """
    import requests
    
    if not isinstance(url, str) or not url.startswith('http'):
        return None
    
    attempts = 0
    tokens_tried = set()
    requester = session if session else requests
    
    while attempts < max_retries:
        try:
            headers = token_manager.get_headers()
            current_token = token_manager.get_current_token()
            
            # Check if we've tried all available tokens
            if current_token in tokens_tried and len(tokens_tried) >= token_manager.get_token_count():
                print(f"⚠️  All {token_manager.get_token_count()} token(s) failed for {url}")
                return None
            
            tokens_tried.add(current_token)
            response = requester.get(url, headers=headers, timeout=timeout)
            
            if response.status_code == 200:
                return response
            elif response.status_code in [403, 429]:  # Rate limit or forbidden
                print(f"⚠️  Rate limited (HTTP {response.status_code}) for {url[:80]}...")
                if token_manager.has_more_tokens():
                    token_manager.rotate_token()
                    time.sleep(1)
                    attempts += 1
                    continue
                else:
                    print(f"⚠️  Only one token available and it's rate limited")
                    return None
            elif response.status_code == 401:  # Unauthorized
                print(f"⚠️  Token unauthorized (HTTP 401) for {url[:80]}...")
                if token_manager.has_more_tokens():
                    token_manager.rotate_token()
                    time.sleep(1)
                    attempts += 1
                    continue
                else:
                    print(f"⚠️  Only one token available and it's invalid")
                    return None
            else:
                # Other error - return the response so caller can handle it
                return response
                
        except requests.exceptions.Timeout:
            print(f"⏱️  Timeout for {url[:80]}... (attempt {attempts + 1}/{max_retries})")
            attempts += 1
            time.sleep(2)
        except requests.exceptions.RequestException as e:
            print(f"⚠️  Request error for {url[:80]}...: {e}")
            attempts += 1
            time.sleep(2)
    
    print(f"⚠️  Max retries ({max_retries}) exceeded for {url[:80]}...")
    return None


# Convenience function for getting just the text content
def fetch_text_with_token_rotation(url, session=None, max_retries=3, timeout=10):
    """
    Fetch text content from URL with automatic token rotation.
    
    Args:
        url: URL to fetch
        session: Optional requests.Session object
        max_retries: Maximum retry attempts
        timeout: Request timeout in seconds
    
    Returns:
        str: Text content or None on failure
    """
    response = fetch_with_token_rotation(url, session, max_retries, timeout)
    if response and response.status_code == 200:
        return response.text
    return None
