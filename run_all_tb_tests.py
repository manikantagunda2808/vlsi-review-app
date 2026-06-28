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
        "name": "T1 — TB001 fail: module has ports",
        "code": """module test(input clk, output out);
  assign out = clk;
endmodule""",
        "expect": {"TB001":"fail","TB002":"pass","TB003":"pass","TB005":"pass","TB006":"fail","TB007":"fail","TB008":"pass","TB010":"pass"}
    },
    {
        "name": "T2 — TB001 pass: no ports",
        "code": """module test;
  initial begin
    $display("hello");
    #100 $finish;
  end
endmodule""",
        "expect": {"TB001":"pass","TB002":"pass","TB003":"fail","TB005":"pass","TB006":"pass","TB007":"fail","TB008":"fail","TB010":"pass"}
    },
    {
        "name": "T3 — TB002 fail: positional connections",
        "code": """module test;
  my_dut dut (.clk(clk), .rst_n(rst_n), .data(data));
  initial #100 $finish;
endmodule""",
        "expect": {"TB001":"pass","TB002":"pass","TB003":"fail","TB005":"fail","TB006":"pass","TB007":"fail","TB008":"fail","TB010":"pass"}
    },
    {
        "name": "T4 — TB003 fail: no parameterized clock period",
        "code": """module test;
  logic clk;
  always #5 clk = ~clk;
  initial #100 $finish;
endmodule""",
        "expect": {"TB001":"pass","TB002":"pass","TB003":"fail","TB005":"pass","TB006":"pass","TB007":"fail","TB008":"fail","TB010":"pass"}
    },
    {
        "name": "T5 — TB003 pass: parameterized clock period",
        "code": """module test;
  parameter CLK_PERIOD = 10;
  logic clk;
  always #(CLK_PERIOD/2) clk = ~clk;
  initial #100 $finish;
endmodule""",
        "expect": {"TB001":"pass","TB002":"pass","TB003":"pass","TB005":"pass","TB006":"pass","TB007":"fail","TB008":"fail","TB010":"pass"}
    },
    {
        "name": "T6 — TB005 fail: missing reg or wire",
        "code": """module test;
  my_dut dut (.clk(clk));
  initial #100 $finish;
endmodule""",
        "expect": {"TB001":"pass","TB002":"pass","TB003":"fail","TB005":"fail","TB006":"pass","TB007":"fail","TB008":"fail","TB010":"pass"}
    },
    {
        "name": "T7 — TB005 pass: reg and wire present",
        "code": """module test;
  reg clk;
  wire [7:0] data;
  my_dut dut (.clk(clk), .data(data));
  initial #100 $finish;
endmodule""",
        "expect": {"TB001":"pass","TB002":"pass","TB003":"fail","TB005":"pass","TB006":"pass","TB007":"fail","TB008":"fail","TB010":"pass"}
    },
    {
        "name": "T8 — TB006 pass: timeout watchdog",
        "code": """module test;
  initial begin
    #1000 $finish;
    forever @(posedge clk) /* test */;
  end
endmodule""",
        "expect": {"TB001":"pass","TB002":"pass","TB003":"fail","TB005":"pass","TB006":"pass","TB007":"fail","TB008":"fail","TB010":"pass"}
    },
    {
        "name": "T9 — TB006 fail: no timeout",
        "code": """module test;
  initial begin
    forever @(posedge clk) /* test */;
  end
endmodule""",
        "expect": {"TB001":"pass","TB002":"pass","TB003":"fail","TB005":"pass","TB006":"fail","TB007":"fail","TB008":"pass","TB010":"pass"}
    },
    {
        "name": "T10 — TB007 pass: $display with $time",
        "code": """module test;
  initial begin
    $display("time=%0t val=%0d", $time, val);
    #100 $finish;
  end
endmodule""",
        "expect": {"TB001":"pass","TB002":"pass","TB003":"fail","TB005":"pass","TB006":"pass","TB007":"pass","TB008":"fail","TB010":"pass"}
    },
    {
        "name": "T11 — TB007 fail: $display without $time",
        "code": """module test;
  initial begin
    $display("hello");
    #100 $finish;
  end
endmodule""",
        "expect": {"TB001":"pass","TB002":"pass","TB003":"fail","TB005":"pass","TB006":"pass","TB007":"fail","TB008":"fail","TB010":"pass"}
    },
    {
        "name": "T12 — TB008 fail: bare $finish",
        "code": """module test;
  initial begin
    #100;
    $finish;
  end
endmodule""",
        "expect": {"TB001":"pass","TB002":"pass","TB003":"fail","TB005":"pass","TB006":"fail","TB007":"fail","TB008":"fail","TB010":"pass"}
    },
    {
        "name": "T13 — TB008 pass: $finish with PASS/FAIL",
        "code": """module test;
  initial begin
    #100;
    $display("PASS: all tests passed");
    $finish;
  end
endmodule""",
        "expect": {"TB001":"pass","TB002":"pass","TB003":"fail","TB005":"pass","TB006":"fail","TB007":"fail","TB008":"pass","TB010":"pass"}
    },
    {
        "name": "T14 — TB010 pass: filename tb_*.v",
        "code": """### tb_my_dut.v
module test;
  initial begin
    #100 $finish;
  end
endmodule""",
        "expect": {"TB001":"pass","TB002":"pass","TB003":"fail","TB005":"pass","TB006":"pass","TB007":"fail","TB008":"fail","TB010":"pass"}
    },
    {
        "name": "T15 — TB010 fail: wrong filename",
        "code": """### my_dut_tb.v
module test;
  initial begin
    #100 $finish;
  end
endmodule""",
        "expect": {"TB001":"pass","TB002":"pass","TB003":"fail","TB005":"pass","TB006":"pass","TB007":"fail","TB008":"fail","TB010":"fail"}
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
        "code": code, "review_type": "verilog_tb", "user_name": "Manikanta"
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
    for rid in {"TB004","TB009"}:
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

with open("test_tb_report.json", "w") as f:
    json.dump(results_log, f, indent=2, ensure_ascii=False)
print("Report saved to test_tb_report.json", flush=True)
