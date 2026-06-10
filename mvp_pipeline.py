
import json
import os

def run_construct_ai_pipeline(request_data):
    # 1. Field Supervisor
    field_scope = {"work_type": request_data['work_type'], "qty": request_data['qty'], "location": request_data['location']}
    print(f"Field Supervisor identified scope: {field_scope}")
    
    # 2. Estimation Engineer
    unit_price = 1500
    total = unit_price * field_scope['qty']
    estimation = {"item": field_scope['work_type'], "total": total, "unit_price": unit_price}
    print(f"Estimation Engineer calculated: {estimation}")
    
    # 3. Risk Analyst
    risk_margin = 1.15
    final_total = estimation['total'] * risk_margin
    print(f"Risk Analyst applied margin: {final_total}")
    
    # 4. Final Reviewer
    final_report = {
        "request": request_data,
        "breakdown": estimation,
        "final_total": final_total,
        "status": "APPROVED"
    }
    
    os.makedirs('/home/user/construct_ai/output', exist_ok=True)
    with open('/home/user/construct_ai/output/estimate_mvp.json', 'w') as f:
        json.dump(final_report, f, indent=2)
    
    return final_report

if __name__ == '__main__':
    test_request = {"work_type": "Interior Painting", "qty": 100, "location": "Osaka"}
    run_construct_ai_pipeline(test_request)
