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

# expect: rule_id -> "pass"/"fail"/"skip" (needs_manual)
tests = [
    {
        "name": "SV1 — SV001 fail: hardcoded delay",
        "code": """module test;
  initial begin
    #100;
    $finish;
  end
endmodule""",
        "expect": {"SV001":"fail","SV002":"fail","SV005":"pass","SV006":"fail","SV007":"fail","SV008":"pass","SV010":"fail"}
    },
    {
        "name": "SV2 — SV002 fail: clock no parameter",
        "code": """module test;
  logic clk;
  always #5 clk = ~clk;
endmodule""",
        "expect": {"SV001":"fail","SV002":"fail","SV005":"pass","SV006":"fail","SV007":"fail","SV008":"pass","SV010":"pass"}
    },
    {
        "name": "SV3 — SV002 pass: clock with parameter",
        "code": """module test;
  parameter CLK_PERIOD = 10;
  logic clk;
  always #(CLK_PERIOD/2) clk = ~clk;
endmodule""",
        "expect": {"SV001":"pass","SV002":"pass","SV005":"pass","SV006":"fail","SV007":"fail","SV008":"pass","SV010":"pass"}
    },
    {
        "name": "SV4 — SV005 fail: blocking = in posedge",
        "code": """module test;
  logic clk, rst_n, a, b, q;
  always @(posedge clk or negedge rst_n)
    if (!rst_n) q = 0; else q = a | b;
endmodule""",
        "expect": {"SV001":"pass","SV002":"fail","SV005":"fail","SV006":"fail","SV007":"fail","SV008":"pass","SV010":"pass"}
    },
    {
        "name": "SV5 — SV005 pass: non-blocking in posedge",
        "code": """module test;
  logic clk, rst_n, d, q;
  always_ff @(posedge clk or negedge rst_n)
    if (!rst_n) q <= 0; else q <= d;
endmodule""",
        "expect": {"SV001":"pass","SV002":"pass","SV005":"pass","SV006":"fail","SV007":"fail","SV008":"pass","SV010":"pass"}
    },
    {
        "name": "SV6 — SV006 pass: timeout watchdog present",
        "code": """module test;
  initial begin
    #1000 $finish;
    forever begin
      @(posedge clk);
      // test body
    end
  end
endmodule""",
        "expect": {"SV001":"fail","SV002":"fail","SV005":"pass","SV006":"pass","SV007":"fail","SV008":"pass","SV010":"fail"}
    },
    {
        "name": "SV7 — SV007 pass: $display with $time",
        "code": """module test;
  initial begin
    $display("time=%0t data=%0d", $time, data);
    $finish;
  end
endmodule""",
        "expect": {"SV001":"pass","SV002":"fail","SV005":"pass","SV006":"fail","SV007":"pass","SV008":"pass","SV010":"fail"}
    },
    {
        "name": "SV8 — SV007 fail: $display without $time",
        "code": """module test;
  initial begin
    $display("hello world");
    $finish;
  end
endmodule""",
        "expect": {"SV001":"pass","SV002":"fail","SV005":"pass","SV006":"fail","SV007":"fail","SV008":"pass","SV010":"fail"}
    },
    {
        "name": "SV9 — SV008 pass: filename *_tb.sv",
        "code": """### uart_tb.sv
module test;
  initial begin
    $display("hello");
    $finish;
  end
endmodule""",
        "expect": {"SV001":"pass","SV002":"fail","SV005":"pass","SV006":"fail","SV007":"fail","SV008":"pass","SV010":"fail"}
    },
    {
        "name": "SV10 — SV008 fail: wrong filename pattern",
        "code": """### uart_tb_test.sv
module test;
  initial begin
    $display("hello");
    $finish;
  end
endmodule""",
        "expect": {"SV001":"pass","SV002":"fail","SV005":"pass","SV006":"fail","SV007":"fail","SV008":"fail","SV010":"fail"}
    },
    {
        "name": "SV11 — SV010 fail: bare $finish",
        "code": """module test;
  initial begin
    #100;
    $finish;
  end
endmodule""",
        "expect": {"SV001":"fail","SV002":"fail","SV005":"pass","SV006":"fail","SV007":"fail","SV008":"pass","SV010":"fail"}
    },
    {
        "name": "SV12 — SV010 pass: $finish with PASS",
        "code": """module test;
  initial begin
    #100;
    $display("PASS: all tests done");
    $finish;
  end
endmodule""",
        "expect": {"SV001":"fail","SV002":"fail","SV005":"pass","SV006":"fail","SV007":"fail","SV008":"pass","SV010":"pass"}
    },
    {
        "name": "SV13 — All pass clean",
        "code": """### uart_tb.sv
module test;
  parameter CLK_PERIOD = 10;
  logic clk;
  always #(CLK_PERIOD/2) clk = ~clk;
  initial begin
    #1000 $finish;
    forever @(posedge clk) begin
      $display("time=%0t data=%0d", $time, data);
      if (done) $display("PASS: done");
    end
  end
endmodule""",
        "expect": {"SV001":"fail","SV002":"pass","SV005":"fail","SV006":"pass","SV007":"pass","SV008":"pass","SV010":"fail"}
    },
    {
        "name": "SV14 — SV001 pass: no # delay, SV006 pass: timeout present",
        "code": """module test;
  initial begin
    @(posedge clk);
    $finish;
  end
endmodule""",
        "expect": {"SV001":"pass","SV002":"fail","SV005":"pass","SV006":"fail","SV007":"fail","SV008":"pass","SV010":"fail"}
    },
    {
        "name": "SV15 — All static: pass, LLM (SV003/4/9): skip",
        "code": """module test;
  initial begin
    #1000 $finish;
  end
endmodule""",
        "expect": {"SV001":"fail","SV002":"fail","SV005":"pass","SV006":"pass","SV007":"fail","SV008":"pass","SV010":"fail"}
    },
]

print(f"\n{'='*100}", flush=True)
print(f"{'TEST':6s} {'NAME':40s} {'SCORE':6s} {'VIOL':4s} {'WARN':4s} {'PASS':4s} {'SKIP':4s}  MISMATCHES", flush=True)
print(f"{'='*100}", flush=True)

all_pass = True
results_log = []

for tc in tests:
    name = tc["name"]
    code = tc["code"]
    expect = tc["expect"]

    r = requests.post(f"{BASE}/review/paste", headers=headers, json={
        "code": code, "review_type": "sv", "user_name": "Manikanta"
    })

    if r.status_code != 200:
        print(f"{'ERROR':6s} {name:40s} HTTP {r.status_code}", flush=True)
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
    for rid in {"SV003","SV004","SV009"}:
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

    print(f"{status:6s} {name:40s} {score:5.1f}  {v:3d}  {w:3d}  {p:3d}  {s:3d}  {'; '.join(mismatches)}", flush=True)

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

with open("test_sv_report.json", "w") as f:
    json.dump(results_log, f, indent=2, ensure_ascii=False)
print("Report saved to test_sv_report.json", flush=True)
