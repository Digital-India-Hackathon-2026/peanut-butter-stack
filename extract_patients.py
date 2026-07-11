import json
with open('synthetic_dataset/vitalguard_synthetic_dataset.json') as f:
    data = json.load(f)

for p in data['patients']:
    v = p['vitals'][-1] if p['vitals'] else {}
    alerts = p.get('alerts', [])
    alert_types = [a.get('type','') for a in alerts]
    print(p['patient_id'], '|', p['name'], '|', p['age'], p['gender'], '|',
          p['room'], p['bed'], '|',
          'status=' + p['status'], 'severity=' + p['severity'], 'risk=' + str(p['risk_score']), '|',
          p['diagnosis'], '|',
          'Dr=' + p['assigned_doctor'], 'N=' + p['assigned_nurse'], '|',
          'alerts=' + str(len(alerts)), str(alert_types), '|',
          'HR=' + str(round(v.get('heart_rate',0),1)),
          'SpO2=' + str(round(v.get('spo2',0),1)),
          'Temp=' + str(round(v.get('temperature_f',0),1)),
          'ECG=' + str(v.get('ecg_label','?')))
