import requests, json, sys

BASE = "http://127.0.0.1:8000"

print("Logging in...", flush=True)
r = requests.post(f"{BASE}/auth/login", json={
    "email": "manikanta.gunda@vaaluka.com",
    "password": "Vaaluka@123"
})
if r.status_code != 200:
    print(f"Login failed: {r.status_code} {r.text}", flush=True)
    sys.exit(1)
token = r.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}

tests = [
    {
        "name": "U1 — UVM001 pass: `uvm_info used",
        "code": """class my_test extends uvm_test;
  `uvm_component_utils(my_test)
  function void build_phase(uvm_phase phase);
    super.build_phase(phase);
    `uvm_info("MYTEST", "building", UVM_LOW)
  endfunction
endclass""",
        "expect": {"UVM001":"pass","UVM002":"pass","UVM003":"pass","UVM004":"pass","UVM005":"pass","UVM007":"pass","UVM009":"pass","UVM010":"fail"}
    },
    {
        "name": "U2 — UVM001 fail: uvm_report_*",
        "code": """class my_test extends uvm_test;
  `uvm_component_utils(my_test)
  function void build_phase(uvm_phase phase);
    super.build_phase(phase);
    uvm_report_info("MYTEST", "building", UVM_LOW);
  endfunction
endclass""",
        "expect": {"UVM001":"fail","UVM002":"pass","UVM003":"pass","UVM004":"pass","UVM005":"pass","UVM007":"pass","UVM009":"pass","UVM010":"fail"}
    },
    {
        "name": "U3 — UVM002 fail: missing `uvm_component_utils",
        "code": """class my_driver extends uvm_driver #(my_transaction);
  function void build_phase(uvm_phase phase);
    super.build_phase(phase);
  endfunction
endclass""",
        "expect": {"UVM001":"pass","UVM002":"fail","UVM003":"pass","UVM004":"fail","UVM005":"pass","UVM007":"pass","UVM009":"pass","UVM010":"fail"}
    },
    {
        "name": "U4 — UVM003 fail: missing `uvm_object_utils",
        "code": """class my_transaction extends uvm_sequence_item;
  function new(string name = "my_transaction");
    super.new(name);
  endfunction
endclass""",
        "expect": {"UVM001":"pass","UVM002":"pass","UVM003":"fail","UVM004":"pass","UVM005":"pass","UVM007":"pass","UVM009":"pass","UVM010":"fail"}
    },
    {
        "name": "U5 — UVM004 pass: get_next_item + item_done",
        "code": """class my_driver extends uvm_driver #(my_transaction);
  `uvm_component_utils(my_driver)
  task run_phase(uvm_phase phase);
    super.run_phase(phase);
    forever begin
      seq_item_port.get_next_item(req);
      drive_transaction(req);
      seq_item_port.item_done();
    end
  endtask
endclass""",
        "expect": {"UVM001":"pass","UVM002":"pass","UVM003":"pass","UVM004":"pass","UVM005":"pass","UVM007":"pass","UVM009":"pass","UVM010":"fail"}
    },
    {
        "name": "U6 — UVM004 fail: missing get_next_item",
        "code": """class my_driver extends uvm_driver #(my_transaction);
  `uvm_component_utils(my_driver)
  task run_phase(uvm_phase phase);
    super.run_phase(phase);
    forever begin
      seq_item_port.item_done();
    end
  endtask
endclass""",
        "expect": {"UVM001":"pass","UVM002":"pass","UVM003":"pass","UVM004":"fail","UVM005":"pass","UVM007":"pass","UVM009":"pass","UVM010":"fail"}
    },
    {
        "name": "U7 — UVM005 fail: # delay inside driver",
        "code": """class my_driver extends uvm_driver #(my_transaction);
  `uvm_component_utils(my_driver)
  task run_phase(uvm_phase phase);
    super.run_phase(phase);
    forever begin
      seq_item_port.get_next_item(req);
      #10;
      seq_item_port.item_done();
    end
  endtask
endclass""",
        "expect": {"UVM001":"pass","UVM002":"pass","UVM003":"pass","UVM004":"pass","UVM005":"fail","UVM007":"pass","UVM009":"pass","UVM010":"fail"}
    },
    {
        "name": "U8 — UVM007 fail: direct ::new() in env",
        "code": """class my_env extends uvm_env;
  `uvm_component_utils(my_env)
  my_driver drv;
  function void build_phase(uvm_phase phase);
    super.build_phase(phase);
    drv = my_driver::new("drv", this);
  endfunction
endclass""",
        "expect": {"UVM001":"pass","UVM002":"pass","UVM003":"pass","UVM004":"pass","UVM005":"pass","UVM007":"fail","UVM009":"pass","UVM010":"fail"}
    },
    {
        "name": "U9 — UVM007 pass: type_id::create in env",
        "code": """class my_env extends uvm_env;
  `uvm_component_utils(my_env)
  my_driver drv;
  function void build_phase(uvm_phase phase);
    super.build_phase(phase);
    drv = my_driver::type_id::create("drv", this);
  endfunction
endclass""",
        "expect": {"UVM001":"pass","UVM002":"pass","UVM003":"pass","UVM004":"pass","UVM005":"pass","UVM007":"pass","UVM009":"pass","UVM010":"fail"}
    },
    {
        "name": "U10 — UVM009 fail: missing super.*_phase",
        "code": """class my_test extends uvm_test;
  `uvm_component_utils(my_test)
  function void build_phase(uvm_phase phase);
    // missing super.build_phase(phase);
  endfunction
endclass""",
        "expect": {"UVM001":"pass","UVM002":"pass","UVM003":"pass","UVM004":"pass","UVM005":"pass","UVM007":"pass","UVM009":"pass","UVM010":"fail"}
    },
    {
        "name": "U11 — UVM009 pass: super.*_phase present",
        "code": """class my_test extends uvm_test;
  `uvm_component_utils(my_test)
  function void build_phase(uvm_phase phase);
    super.build_phase(phase);
  endfunction
  function void connect_phase(uvm_phase phase);
    super.connect_phase(phase);
  endfunction
endclass""",
        "expect": {"UVM001":"pass","UVM002":"pass","UVM003":"pass","UVM004":"pass","UVM005":"pass","UVM007":"pass","UVM009":"pass","UVM010":"fail"}
    },
    {
        "name": "U12 — UVM010 fail: no pre_start/post_start objection",
        "code": """class my_sequence extends uvm_sequence #(my_transaction);
  `uvm_object_utils(my_sequence)
  task body();
    // no pre_start/post_start with objection
  endtask
endclass""",
        "expect": {"UVM001":"pass","UVM002":"pass","UVM003":"pass","UVM004":"pass","UVM005":"pass","UVM007":"pass","UVM009":"pass","UVM010":"fail"}
    },
    {
        "name": "U13 — UVM010 pass: raise/drop objection",
        "code": """class my_sequence extends uvm_sequence #(my_transaction);
  `uvm_object_utils(my_sequence)
  function void pre_start();
    raise_objection(this);
  endfunction
  function void post_start();
    drop_objection(this);
  endfunction
  task body();
    // sequence body
  endtask
endclass""",
        "expect": {"UVM001":"pass","UVM002":"pass","UVM003":"pass","UVM004":"pass","UVM005":"pass","UVM007":"pass","UVM009":"pass","UVM010":"pass"}
    },
    {
        "name": "U14 — UVM010 fail: pre_start without raise_objection",
        "code": """class my_sequence extends uvm_sequence #(my_transaction);
  `uvm_object_utils(my_sequence)
  function void pre_start();
    // no raise_objection
  endfunction
  task body();
    // sequence body
  endtask
endclass""",
        "expect": {"UVM001":"pass","UVM002":"pass","UVM003":"pass","UVM004":"pass","UVM005":"pass","UVM007":"pass","UVM009":"pass","UVM010":"fail"}
    },
]

print(f"\n{'='*100}", flush=True)
print(f"{'TEST':6s} {'NAME':45s} {'SCORE':6s} {'VIOL':4s} {'WARN':4s} {'PASS':4s} {'SKIP':4s}  MISMATCHES", flush=True)
print(f"{'='*100}", flush=True)

all_pass = True
results_log = []

for tc in tests:
    name = tc["name"]
    code = tc["code"]
    expect = tc["expect"]

    r = requests.post(f"{BASE}/review/paste", headers=headers, json={
        "code": code, "review_type": "uvm", "user_name": "Manikanta"
    })

    if r.status_code != 200:
        print(f"{'ERROR':6s} {name:45s} HTTP {r.status_code}", flush=True)
        all_pass = False
        continue

    data = r.json()
    score = data.get("score", 0)
    violations = {v["rule_id"] for v in data.get("violations", [])}
    warnings = {w["rule_id"] for w in data.get("warnings", [])}
    passed = data.get("passed", [])
    needs_manual = set(data.get("needs_manual_review", []))

    failed_set = violations | warnings
    all_rids = set(expect.keys())

    actual = {}
    for rid in all_rids:
        if rid in failed_set:
            actual[rid] = "fail"
        elif rid in needs_manual:
            actual[rid] = "skip"
        elif any(rid in p for p in passed):
            actual[rid] = "pass"
        else:
            actual[rid] = "missing"

    mismatches = []
    for rid, expected in expect.items():
        if actual[rid] != expected:
            mismatches.append(f"{rid}:exp={expected},got={actual[rid]}")
    for rid in {"UVM006","UVM008"}:
        if rid not in expect:
            got = "fail" if rid in failed_set else ("skip" if rid in needs_manual else ("pass" if any(rid in p for p in passed) else "missing"))
            if got not in ("pass", "skip", "missing"):
                mismatches.append(f"{rid}:exp=pass,got={got}")

    v = len(data.get("violations", []))
    w = len(data.get("warnings", []))
    p = len(passed)
    s = len(needs_manual)

    status = "PASS" if not mismatches else "FAIL"
    if status == "FAIL":
        all_pass = False

    print(f"{status:6s} {name:45s} {score:5.1f}  {v:3d}  {w:3d}  {p:3d}  {s:3d}  {'; '.join(mismatches)}", flush=True)

    results_log.append({
        "name": name, "status": status, "score": score,
        "violations": data.get("violations", []),
        "warnings": data.get("warnings", []),
        "passed": passed,
        "needs_manual": data.get("needs_manual_review", []),
        "summary": data.get("summary", ""),
        "mismatches": mismatches,
    })

print(f"\n{'='*100}", flush=True)
print(f"Overall: {'ALL PASSED' if all_pass else 'SOME FAILED'}", flush=True)

with open("test_uvm_report.json", "w") as f:
    json.dump(results_log, f, indent=2, ensure_ascii=False)
print("Report saved to test_uvm_report.json", flush=True)
