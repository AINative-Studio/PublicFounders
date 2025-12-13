#!/usr/bin/env python3
"""
Test script to verify ZeroDB/AINative API connection
"""
import os
import sys
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

API_KEY = os.getenv('API_KEY')
API_BASE_URL = os.getenv('API_BASE_URL')
EMAIL = os.getenv('EMAIL')
PASSWORD = os.getenv('PASSWORD')

def test_connection():
    """Test basic API connectivity"""
    print("🔍 Testing ZeroDB/AINative API Connection...")
    print(f"📍 Base URL: {API_BASE_URL}")
    print(f"🔑 API Key: {API_KEY[:10]}..." if API_KEY else "❌ No API Key found")
    print()

    if not API_KEY or not API_BASE_URL:
        print("❌ Missing API credentials in .env file")
        return False

    # Test 1: Basic API health check
    print("Test 1: API Health Check")
    try:
        response = requests.get(
            f"{API_BASE_URL}/health",
            headers={"X-API-Key": API_KEY},
            timeout=10
        )
        print(f"   Status Code: {response.status_code}")
        if response.status_code == 200:
            print("   ✅ Health check passed")
        else:
            print(f"   ⚠️  Unexpected response: {response.text}")
    except requests.exceptions.RequestException as e:
        print(f"   ⚠️  Health endpoint not available: {e}")
    print()

    # Test 2: List projects (ZeroDB specific)
    print("Test 2: List ZeroDB Projects")
    try:
        response = requests.get(
            f"{API_BASE_URL}/v1/projects",
            headers={"X-API-Key": API_KEY},
            timeout=10
        )
        print(f"   Status Code: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Projects endpoint accessible")
            print(f"   📊 Response: {data}")
        else:
            print(f"   Response: {response.text}")
    except requests.exceptions.RequestException as e:
        print(f"   ℹ️  Projects endpoint error: {e}")
    print()

    # Test 3: Try vector stats endpoint
    print("Test 3: Vector Database Stats")
    try:
        response = requests.get(
            f"{API_BASE_URL}/v1/vectors/stats",
            headers={"X-API-Key": API_KEY},
            timeout=10
        )
        print(f"   Status Code: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Vector database accessible")
            print(f"   📊 Stats: {data}")
        else:
            print(f"   Response: {response.text}")
    except requests.exceptions.RequestException as e:
        print(f"   ℹ️  Vector stats error: {e}")
    print()

    # Test 4: Try agent memory endpoint
    print("Test 4: Agent Memory API")
    try:
        response = requests.get(
            f"{API_BASE_URL}/v1/memory/status",
            headers={"X-API-Key": API_KEY},
            timeout=10
        )
        print(f"   Status Code: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Agent memory API accessible")
            print(f"   📊 Status: {data}")
        else:
            print(f"   Response: {response.text}")
    except requests.exceptions.RequestException as e:
        print(f"   ℹ️  Memory endpoint error: {e}")
    print()

    print("=" * 60)
    print("🎯 Connection test completed!")
    print("=" * 60)
    return True

if __name__ == "__main__":
    try:
        test_connection()
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        sys.exit(1)
