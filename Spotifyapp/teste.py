# Crie um arquivo fix_json.py na raiz do seu projeto
import json
from pathlib import Path


def fix_json_file(file_path):
    try:
        # 1. Tentar carregar normalmente
        with open(file_path, 'r') as f:
            json.load(f)
        print("✅ JSON válido!")
    except json.JSONDecodeError as e:
        print(f"❌ Erro no JSON: {e}")
        # 2. Corrigir o arquivo
        with open(file_path, 'r') as f:
            content = f.read()

        # Tente corrigir problemas comuns
        fixed_content = content.replace("'", '"')  # Troca aspas simples por duplas
        fixed_content = fixed_content.replace("True", "true").replace("False", "false")

        # Salvar backup
        backup_path = file_path.with_suffix('.json.bak')
        with open(backup_path, 'w') as f:
            f.write(content)

        # Salvar corrigido
        with open(file_path, 'w') as f:
            f.write(fixed_content)

        print(f"🔄 Arquivo corrigido. Backup salvo em {backup_path}")


# Uso:
json_file = Path("dados_ritmo.json")
fix_json_file(json_file)
'''
# clean_json.py
import json


def clean_json(input_file, output_file):
    with open(input_file, 'r') as f:
        data = []
        for line in f:
            try:
                item = json.loads(line)
                data.append(item)
            except:
                continue

    with open(output_file, 'w') as f:
        json.dump(data, f, indent=2)


clean_json('dados_ritmo.json', 'dados_ritmo.json')'''