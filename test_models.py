import os
import requests

def test_api():
    api_key = ''
    with open('.env', 'r', encoding='utf-8') as f:
        for line in f:
            if line.startswith('GEMINI_API_KEY'):
                api_key = line.split('=', 1)[1].strip()
                break

    if not api_key:
        print("API KEY NOT FOUND")
        return

    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
    print(f"Requesting: {url}")
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            models = data.get('models', [])
            print(f"Total models returned: {len(models)}")
            for m in models:
                if 'generateContent' in m.get('supportedGenerationMethods', []):
                    # extract simple name
                    name = m['name'].replace('models/', '')
                    print(f"SUPPORTS GENERATECONTENT -> {name}")
        else:
            print(f"ERROR: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"Exception: {e}")

if __name__ == "__main__":
    test_api()
