
import json
import os
import cognee

def ingest_construction_data(data_list):
    try:
        # Cognee の memory 機能を使い、資材名と単価をナレッジグラフに保存
        for item in data_list:
            entity = f"Material: {item['name']} | Base Price: {item['price']} {item['unit']}"
            cognee.remember(entity)
        
        print(f"Successfully ingested {len(data_list)} construction items into Cognee.")
    except Exception as e:
        print(f"Ingestion error: {e}")

if __name__ == '__main__':
    # テスト用ダミーデータ
    sample_data = [
        {'name': 'Drywall installation', 'price': 2500, 'unit': 'm2'},
        {'name': 'Floor tiling', 'price': 4000, 'unit': 'm2'},
        {'name': 'Electrical wiring', 'price': 8000, 'unit': 'm'}
    ]
    ingest_construction_data(sample_data)
