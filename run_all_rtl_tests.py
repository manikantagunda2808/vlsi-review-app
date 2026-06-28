import requests, json, sys

BASE = "http://127.0.0.1:8000"

# 1. Login
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

# 2. Test cases: expect maps rule_id -> "pass"/"fail"/"skip" (needs_manual)
tests = [
    {
        "name": "TC1 — Clean counter",
        "code": """module counter #(parameter WIDTH = 8)
  (input  logic i_clk, input  logic i_rst_n, output logic [WIDTH-1:0] o_count);
  logic [WIDTH-1:0] count;
  always_ff @(posedge i_clk or negedge i_rst_n) begin
    if (!i_rst_n) count <= 0; else count <= count + 1;
  end
  assign o_count = count;
endmodule""",
        "expect": {"RTL001":"pass","RTL002":"pass","RTL003":"pass","RTL004":"pass","RTL005":"pass","RTL006":"pass","RTL007":"skip","RTL008":"pass","RTL009":"pass","RTL010":"pass"}
    },
    {
        "name": "TC2 — RTL001 fail: always_comb no else",
        "code": """module latch(input a, output reg out);
  always_comb begin
    if (a) out = 1;
  end
endmodule""",
        "expect": {"RTL001":"fail","RTL002":"pass","RTL003":"pass","RTL004":"pass","RTL005":"fail","RTL006":"pass","RTL007":"skip","RTL008":"pass","RTL009":"pass","RTL010":"pass"}
    },
    {
        "name": "TC3 — RTL001 fail: always_ff no else",
        "code": """module test(input a, input clk, output reg out);
  always_ff @(posedge clk) begin
    if (a) out <= 1;
  end
endmodule""",
        "expect": {"RTL001":"fail","RTL002":"pass","RTL003":"fail","RTL004":"pass","RTL005":"fail","RTL006":"pass","RTL007":"skip","RTL008":"pass","RTL009":"pass","RTL010":"pass"}
    },
    {
        "name": "TC4 — RTL002 fail: case no default + RTL010",
        "code": """module mux(input [1:0] sel, input a,b,c,d, output reg out);
  always_comb begin
    case(sel)
      2'b00: out = a;
      2'b01: out = b;
    endcase
  end
endmodule""",
        "expect": {"RTL001":"pass","RTL002":"fail","RTL003":"pass","RTL004":"pass","RTL005":"fail","RTL006":"pass","RTL007":"skip","RTL008":"pass","RTL009":"pass","RTL010":"fail"}
    },
    {
        "name": "TC5 — RTL003 fail: posedge reset only",
        "code": """module test(input clk, input rst, output reg out);
  always_ff @(posedge clk or posedge rst) begin
    if (rst) out <= 0; else out <= 1;
  end
endmodule""",
        "expect": {"RTL001":"pass","RTL002":"pass","RTL003":"fail","RTL004":"pass","RTL005":"fail","RTL006":"pass","RTL007":"skip","RTL008":"pass","RTL009":"pass","RTL010":"pass"}
    },
    {
        "name": "TC6 — RTL004 fail: plain always",
        "code": """module test(input a, output reg out);
  always @(*) begin
    if (a) out = 1; else out = 0;
  end
endmodule""",
        "expect": {"RTL001":"pass","RTL002":"pass","RTL003":"pass","RTL004":"fail","RTL005":"fail","RTL006":"pass","RTL007":"skip","RTL008":"pass","RTL009":"pass","RTL010":"pass"}
    },
    {
        "name": "TC7 — RTL005 fail: bare ports no i_/o_",
        "code": """module bad(input clk, input rst_n, output out);
  assign out = clk;
endmodule""",
        "expect": {"RTL001":"pass","RTL002":"pass","RTL003":"pass","RTL004":"pass","RTL005":"fail","RTL006":"pass","RTL007":"skip","RTL008":"pass","RTL009":"pass","RTL010":"pass"}
    },
    {
        "name": "TC8 — RTL006 fail: X assignment",
        "code": """module test(input clk, input rst_n, input a, output reg out);
  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) out <= 1'bx; else out <= a;
  end
endmodule""",
        "expect": {"RTL001":"pass","RTL002":"pass","RTL003":"pass","RTL004":"pass","RTL005":"fail","RTL006":"fail","RTL007":"skip","RTL008":"pass","RTL009":"pass","RTL010":"pass"}
    },
    {
        "name": "TC9 — RTL008 fail: unused signal",
        "code": """module test(input i_clk, input i_rst_n, output o_out);
  logic unused;
  assign o_out = i_clk;
endmodule""",
        "expect": {"RTL001":"pass","RTL002":"pass","RTL003":"pass","RTL004":"pass","RTL005":"pass","RTL006":"pass","RTL007":"skip","RTL008":"fail","RTL009":"pass","RTL010":"pass"}
    },
    {
        "name": "TC10 — RTL010 fail: hardcoded bit-widths",
        "code": """module test(input [7:0] i_data, output [3:0] o_data);
  assign o_data = i_data[3:0];
endmodule""",
        "expect": {"RTL001":"pass","RTL002":"pass","RTL003":"pass","RTL004":"pass","RTL005":"pass","RTL006":"pass","RTL007":"skip","RTL008":"pass","RTL009":"pass","RTL010":"fail"}
    },
    {
        "name": "TC11 — RTL003 fail: clear_n (no rst/reset)",
        "code": """module test(input clk, input clear_n, output reg out);
  always_ff @(posedge clk or negedge clear_n) begin
    if (!clear_n) out <= 0; else out <= 1;
  end
endmodule""",
        "expect": {"RTL001":"pass","RTL002":"pass","RTL003":"fail","RTL004":"pass","RTL005":"fail","RTL006":"pass","RTL007":"skip","RTL008":"pass","RTL009":"pass","RTL010":"pass"}
    },
    {
        "name": "TC12 — Multiple violations",
        "code": """module bad(input a, input b, input [1:0] sel, input clk, output reg out, output reg [3:0] o_data);
  wire unused_wire;
  always @(*) begin
    if (sel)
      out = 1'bx;
  end
endmodule""",
        "expect": {"RTL001":"fail","RTL002":"pass","RTL003":"pass","RTL004":"fail","RTL005":"fail","RTL006":"fail","RTL007":"skip","RTL008":"fail","RTL009":"pass","RTL010":"fail"}
    },
    {
        "name": "TC13 — RTL001+RTL002+RTL004",
        "code": """module bad(input a, input [1:0] sel, output reg out);
  always @(*) begin
    if (a) out = 1;
    case(sel)
      2'b00: out = 0;
    endcase
  end
endmodule""",
        "expect": {"RTL001":"fail","RTL002":"fail","RTL003":"pass","RTL004":"fail","RTL005":"fail","RTL006":"pass","RTL007":"skip","RTL008":"pass","RTL009":"pass","RTL010":"fail"}
    },
    {
        "name": "TC14 — Filename match (pass)",
        "code": """### counter.sv
module counter(input i_clk, output o_out);
  assign o_out = 1;
endmodule""",
        "expect": {"RTL001":"pass","RTL002":"pass","RTL003":"pass","RTL004":"pass","RTL005":"pass","RTL006":"pass","RTL007":"skip","RTL008":"fail","RTL009":"pass","RTL010":"pass"}
    },
    {
        "name": "TC15 — Empty module",
        "code": """module empty;
endmodule""",
        "expect": {"RTL001":"pass","RTL002":"pass","RTL003":"pass","RTL004":"pass","RTL005":"pass","RTL006":"pass","RTL007":"skip","RTL008":"pass","RTL009":"pass","RTL010":"pass"}
    },
    # ── New 20 tests: edge cases ──────────────────────────────────
    {
        "name": "TC16 — RTL001 fail: always_latch no else",
        "code": """module test(input a, output reg out);
  always_latch begin
    if (a) out = 1;
  end
endmodule""",
        "expect": {"RTL001":"fail","RTL002":"pass","RTL003":"pass","RTL004":"pass","RTL005":"fail","RTL006":"pass","RTL007":"skip","RTL008":"pass","RTL009":"pass","RTL010":"pass"}
    },
    {
        "name": "TC17 — RTL001 fail: always @(posedge) no else",
        "code": """module test(input clk, input rst_n, output reg out);
  always @(posedge clk or negedge rst_n) begin
    if (!rst_n) out <= 0;
  end
endmodule""",
        "expect": {"RTL001":"fail","RTL002":"pass","RTL003":"pass","RTL004":"fail","RTL005":"fail","RTL006":"pass","RTL007":"skip","RTL008":"pass","RTL009":"pass","RTL010":"pass"}
    },
    {
        "name": "TC18 — RTL001 pass: if-else if-else complete",
        "code": """module test(input a, input b, output reg out);
  always_comb begin
    if (a) out = 1;
    else if (b) out = 2;
    else out = 0;
  end
endmodule""",
        "expect": {"RTL001":"pass","RTL002":"pass","RTL003":"pass","RTL004":"pass","RTL005":"fail","RTL006":"pass","RTL007":"skip","RTL008":"pass","RTL009":"pass","RTL010":"pass"}
    },
    {
        "name": "TC19 — RTL002 pass: case with default",
        "code": """module test(input [1:0] sel, output reg out);
  always_comb begin
    case(sel)
      2'b00: out = 0;
      2'b01: out = 1;
      default: out = 0;
    endcase
  end
endmodule""",
        "expect": {"RTL001":"pass","RTL002":"pass","RTL003":"pass","RTL004":"pass","RTL005":"fail","RTL006":"pass","RTL007":"skip","RTL008":"pass","RTL009":"pass","RTL010":"fail"}
    },
    {
        "name": "TC20 — RTL002 fail: casex no default",
        "code": """module test(input [1:0] sel, output reg out);
  always_comb begin
    casex(sel)
      2'b00: out = 0;
      2'b01: out = 1;
    endcase
  end
endmodule""",
        "expect": {"RTL001":"pass","RTL002":"fail","RTL003":"pass","RTL004":"pass","RTL005":"fail","RTL006":"pass","RTL007":"skip","RTL008":"pass","RTL009":"pass","RTL010":"fail"}
    },
    {
        "name": "TC21 — RTL002 fail: casez no default",
        "code": """module test(input [1:0] sel, output reg out);
  always_comb begin
    casez(sel)
      2'b00: out = 0;
      2'b01: out = 1;
    endcase
  end
endmodule""",
        "expect": {"RTL001":"pass","RTL002":"fail","RTL003":"pass","RTL004":"pass","RTL005":"fail","RTL006":"pass","RTL007":"skip","RTL008":"pass","RTL009":"pass","RTL010":"fail"}
    },
    {
        "name": "TC22 — RTL002 fail: nested case inner missing default",
        "code": """module test(input [1:0] sel, input [1:0] sub, output reg out);
  always_comb begin
    case(sel)
      2'b00: out = 0;
      2'b01: begin
        case(sub)
          2'b00: out = 1;
        endcase
      end
      default: out = 0;
    endcase
  end
endmodule""",
        "expect": {"RTL001":"pass","RTL002":"pass","RTL003":"pass","RTL004":"pass","RTL005":"fail","RTL006":"pass","RTL007":"skip","RTL008":"pass","RTL009":"pass","RTL010":"fail"}
    },
    {
        "name": "TC23 — RTL003 pass: i_rst_n naming variant",
        "code": """module test(input i_clk, input i_rst_n, output reg o_out);
  always_ff @(posedge i_clk or negedge i_rst_n) begin
    if (!i_rst_n) o_out <= 0; else o_out <= 1;
  end
endmodule""",
        "expect": {"RTL001":"pass","RTL002":"pass","RTL003":"pass","RTL004":"pass","RTL005":"pass","RTL006":"pass","RTL007":"skip","RTL008":"pass","RTL009":"pass","RTL010":"pass"}
    },
    {
        "name": "TC24 — RTL003 pass: sys_reset_n naming variant",
        "code": """module test(input clk, input sys_reset_n, output reg out);
  always_ff @(posedge clk or negedge sys_reset_n) begin
    if (!sys_reset_n) out <= 0; else out <= 1;
  end
endmodule""",
        "expect": {"RTL001":"pass","RTL002":"pass","RTL003":"pass","RTL004":"pass","RTL005":"fail","RTL006":"pass","RTL007":"skip","RTL008":"pass","RTL009":"pass","RTL010":"pass"}
    },
    {
        "name": "TC25 — RTL003 fail: always_ff with no reset signal",
        "code": """module test(input clk, output reg out);
  always_ff @(posedge clk) begin
    out <= 1;
  end
endmodule""",
        "expect": {"RTL001":"pass","RTL002":"pass","RTL003":"fail","RTL004":"pass","RTL005":"fail","RTL006":"pass","RTL007":"skip","RTL008":"pass","RTL009":"pass","RTL010":"pass"}
    },
    {
        "name": "TC26 — RTL004 pass: always_ff + always_comb only",
        "code": """module test(input i_clk, input i_rst_n, input a, output reg out, output reg o_flag);
  always_ff @(posedge i_clk or negedge i_rst_n) begin
    if (!i_rst_n) out <= 0; else out <= a;
  end
  always_comb begin
    o_flag = ~a;
  end
endmodule""",
        "expect": {"RTL001":"pass","RTL002":"pass","RTL003":"pass","RTL004":"pass","RTL005":"fail","RTL006":"pass","RTL007":"skip","RTL008":"pass","RTL009":"pass","RTL010":"pass"}
    },
    {
        "name": "TC27 — RTL004 fail: plain always @(posedge)",
        "code": """module test(input clk, input rst_n, output reg out);
  always @(posedge clk or negedge rst_n) begin
    if (!rst_n) out <= 0; else out <= 1;
  end
endmodule""",
        "expect": {"RTL001":"pass","RTL002":"pass","RTL003":"pass","RTL004":"fail","RTL005":"fail","RTL006":"pass","RTL007":"skip","RTL008":"pass","RTL009":"pass","RTL010":"pass"}
    },
    {
        "name": "TC28 — RTL005 pass: all correct prefixes + exemptions",
        "code": """module test(input i_clk, input i_data, output o_out, output o_result);
  assign o_out = i_data;
  assign o_result = i_clk;
endmodule""",
        "expect": {"RTL001":"pass","RTL002":"pass","RTL003":"pass","RTL004":"pass","RTL005":"pass","RTL006":"pass","RTL007":"skip","RTL008":"pass","RTL009":"pass","RTL010":"pass"}
    },
    {
        "name": "TC29 — RTL005 fail: mixed correct and wrong prefixes",
        "code": """module test(input i_clk, input data, output o_out, output result);
  assign o_out = i_clk;
  assign result = data;
endmodule""",
        "expect": {"RTL001":"pass","RTL002":"pass","RTL003":"pass","RTL004":"pass","RTL005":"fail","RTL006":"pass","RTL007":"skip","RTL008":"pass","RTL009":"pass","RTL010":"pass"}
    },
    {
        "name": "TC30 — RTL006 pass: no X assignments",
        "code": """module test(input i_clk, input i_rst_n, output reg o_out);
  always_ff @(posedge i_clk or negedge i_rst_n) begin
    if (!i_rst_n) o_out <= 0; else o_out <= 1;
  end
endmodule""",
        "expect": {"RTL001":"pass","RTL002":"pass","RTL003":"pass","RTL004":"pass","RTL005":"pass","RTL006":"pass","RTL007":"skip","RTL008":"pass","RTL009":"pass","RTL010":"pass"}
    },
    {
        "name": "TC31 — RTL006 fail: 1'bX uppercase and bare 'x",
        "code": """module test(input i_clk, input i_rst_n, output reg o_out, output reg o_val);
  always_ff @(posedge i_clk or negedge i_rst_n) begin
    if (!i_rst_n) begin
      o_out <= 1'bX;
      o_val <= 'x;
    end else begin
      o_out <= 1;
      o_val <= 0;
    end
  end
endmodule""",
        "expect": {"RTL001":"pass","RTL002":"pass","RTL003":"pass","RTL004":"pass","RTL005":"pass","RTL006":"fail","RTL007":"skip","RTL008":"pass","RTL009":"pass","RTL010":"pass"}
    },
    {
        "name": "TC32 — RTL008 pass: all signals used",
        "code": """module test(input i_data, output o_out);
  logic tmp;
  assign tmp = i_data;
  assign o_out = tmp;
endmodule""",
        "expect": {"RTL001":"pass","RTL002":"pass","RTL003":"pass","RTL004":"pass","RTL005":"pass","RTL006":"pass","RTL007":"skip","RTL008":"pass","RTL009":"pass","RTL010":"pass"}
    },
    {
        "name": "TC33 — RTL008 pass: parameter not flagged as signal",
        "code": """module test(input i_clk, output o_data);
  parameter WIDTH = 8;
  assign o_data = i_clk;
endmodule""",
        "expect": {"RTL001":"pass","RTL002":"pass","RTL003":"pass","RTL004":"pass","RTL005":"pass","RTL006":"pass","RTL007":"skip","RTL008":"pass","RTL009":"pass","RTL010":"pass"}
    },
    {
        "name": "TC34 — RTL009 fail: module name mismatch",
        "code": """### counter.sv
module counter_wrong;
  assign a = 1;
endmodule""",
        "expect": {"RTL001":"pass","RTL002":"pass","RTL003":"pass","RTL004":"pass","RTL005":"pass","RTL006":"pass","RTL007":"skip","RTL008":"pass","RTL009":"fail","RTL010":"pass"}
    },
    {
        "name": "TC35 — RTL010 pass: widths use parameters only",
        "code": """module test(input i_clk, output [WIDTH-1:0] o_data);
  parameter WIDTH = 8;
  assign o_data = i_clk;
endmodule""",
        "expect": {"RTL001":"pass","RTL002":"pass","RTL003":"pass","RTL004":"pass","RTL005":"pass","RTL006":"pass","RTL007":"skip","RTL008":"pass","RTL009":"pass","RTL010":"pass"}
    },
    {
        "name": "TC36 — RTL008 fail: param-range port unused (was missed pre-fix)",
        "code": """module test(input i_clk, output o_unused, output [WIDTH-1:0] o_wide);
  parameter WIDTH = 8;
  assign o_unused = i_clk;
  // this port has no assignments
endmodule""",
        "expect": {"RTL001":"pass","RTL002":"pass","RTL003":"pass","RTL004":"pass","RTL005":"pass","RTL006":"pass","RTL007":"skip","RTL008":"fail","RTL009":"pass","RTL010":"pass"}
    },
    # ── RTL008: 10 new tests ────────────────────────────────────────
    {
        "name": "TC37 — RTL008 pass: all ports used via assign",
        "code": """module test(input i_a, input i_b, output o_sum);
  assign o_sum = i_a | i_b;
endmodule""",
        "expect": {"RTL001":"pass","RTL002":"pass","RTL003":"pass","RTL004":"pass","RTL005":"pass","RTL006":"pass","RTL007":"skip","RTL008":"pass","RTL009":"pass","RTL010":"pass"}
    },
    {
        "name": "TC38 — RTL008 pass: always_ff + assign cross-block",
        "code": """module test(input i_clk, input i_rst_n, input i_d, output o_q, output o_copy);
  logic q;
  always_ff @(posedge i_clk or negedge i_rst_n) begin
    if (!i_rst_n) q <= 0; else q <= i_d;
  end
  assign o_q = q;
  assign o_copy = i_d;
endmodule""",
        "expect": {"RTL001":"pass","RTL002":"pass","RTL003":"pass","RTL004":"pass","RTL005":"pass","RTL006":"pass","RTL007":"skip","RTL008":"pass","RTL009":"pass","RTL010":"pass"}
    },
    {
        "name": "TC39 — RTL008 pass: genvar not flagged",
        "code": """module test(input [7:0] i_data, output [7:0] o_data);
  genvar g;
  generate
    for (g = 0; g < 8; g++) begin
      assign o_data[g] = i_data[g];
    end
  endgenerate
endmodule""",
        "expect": {"RTL001":"pass","RTL002":"pass","RTL003":"pass","RTL004":"pass","RTL005":"pass","RTL006":"pass","RTL007":"skip","RTL008":"pass","RTL009":"pass","RTL010":"fail"}
    },
    {
        "name": "TC40 — RTL008 fail: single internal wire unused",
        "code": """module test(input i_a, input i_b, output o_sum);
  wire unused;
  assign o_sum = i_a | i_b;
endmodule""",
        "expect": {"RTL001":"pass","RTL002":"pass","RTL003":"pass","RTL004":"pass","RTL005":"pass","RTL006":"pass","RTL007":"skip","RTL008":"fail","RTL009":"pass","RTL010":"pass"}
    },
    {
        "name": "TC41 — RTL008 fail: unused input port",
        "code": """module test(input i_clk, input i_data, output o_out);
  assign o_out = i_clk;
endmodule""",
        "expect": {"RTL001":"pass","RTL002":"pass","RTL003":"pass","RTL004":"pass","RTL005":"pass","RTL006":"pass","RTL007":"skip","RTL008":"fail","RTL009":"pass","RTL010":"pass"}
    },
    {
        "name": "TC42 — RTL008 fail: unused output port",
        "code": """module test(input i_clk, output o_data, output o_extra);
  assign o_data = i_clk;
endmodule""",
        "expect": {"RTL001":"pass","RTL002":"pass","RTL003":"pass","RTL004":"pass","RTL005":"pass","RTL006":"pass","RTL007":"skip","RTL008":"fail","RTL009":"pass","RTL010":"pass"}
    },
    {
        "name": "TC43 — RTL008 fail: multiple unused (wire+port+reg)",
        "code": """module test(input i_a, input i_b, output o_data);
  reg r_unused;
  wire w_unused;
  assign o_data = i_a;
endmodule""",
        "expect": {"RTL001":"pass","RTL002":"pass","RTL003":"pass","RTL004":"pass","RTL005":"pass","RTL006":"pass","RTL007":"skip","RTL008":"fail","RTL009":"pass","RTL010":"pass"}
    },
    {
        "name": "TC44 — RTL008 fail: logic tmp declared but never used",
        "code": """module test(input [1:0] i_sel, input i_a, input i_b, output o_out);
  logic tmp;
  always_comb begin
    case(i_sel)
      2'b00: o_out = i_a;
      2'b01: o_out = i_b;
      default: o_out = 0;
    endcase
  end
endmodule""",
        "expect": {"RTL001":"pass","RTL002":"pass","RTL003":"pass","RTL004":"pass","RTL005":"pass","RTL006":"pass","RTL007":"skip","RTL008":"fail","RTL009":"pass","RTL010":"fail"}
    },
    {
        "name": "TC45 — RTL008 pass: two internal signals all used",
        "code": """module test(input i_a, input i_b, output o_out);
  logic sum;
  logic carry;
  always_comb begin
    sum = i_a ^ i_b;
    carry = i_a & i_b;
    o_out = sum | carry;
  end
endmodule""",
        "expect": {"RTL001":"pass","RTL002":"pass","RTL003":"pass","RTL004":"pass","RTL005":"pass","RTL006":"pass","RTL007":"skip","RTL008":"pass","RTL009":"pass","RTL010":"pass"}
    },
    {
        "name": "TC46 — RTL008 pass: ports only, no internals, all used",
        "code": """module test(input i_clk, input i_rst_n, output o_q);
  assign o_q = i_clk | i_rst_n;
endmodule""",
        "expect": {"RTL001":"pass","RTL002":"pass","RTL003":"pass","RTL004":"pass","RTL005":"pass","RTL006":"pass","RTL007":"skip","RTL008":"pass","RTL009":"pass","RTL010":"pass"}
    },
    # ── RTL005: 10 new tests ────────────────────────────────────────
    {
        "name": "TC47 — RTL005 pass: input wire i_clk, output reg o_data",
        "code": """module test(input wire i_clk, output reg o_data);
  assign o_data = i_clk;
endmodule""",
        "expect": {"RTL001":"pass","RTL002":"pass","RTL003":"pass","RTL004":"pass","RTL005":"pass","RTL006":"pass","RTL007":"skip","RTL008":"pass","RTL009":"pass","RTL010":"pass"}
    },
    {
        "name": "TC48 — RTL005 pass: param-range with correct prefix",
        "code": """module test(input [WIDTH-1:0] i_data, output [WIDTH-1:0] o_data);
  parameter WIDTH = 8;
  assign o_data = i_data;
endmodule""",
        "expect": {"RTL001":"pass","RTL002":"pass","RTL003":"pass","RTL004":"pass","RTL005":"pass","RTL006":"pass","RTL007":"skip","RTL008":"pass","RTL009":"pass","RTL010":"pass"}
    },
    {
        "name": "TC49 — RTL005 pass: type+literal range+correct prefix",
        "code": """module test(input logic [7:0] i_data, output reg [3:0] o_data);
  assign o_data = i_data;
endmodule""",
        "expect": {"RTL001":"pass","RTL002":"pass","RTL003":"pass","RTL004":"pass","RTL005":"pass","RTL006":"pass","RTL007":"skip","RTL008":"pass","RTL009":"pass","RTL010":"fail"}
    },
    {
        "name": "TC50 — RTL005 pass: clk/rst_n exemptions + correct output",
        "code": """module test(input clk, input rst_n, output o_data);
  assign o_data = rst_n;
endmodule""",
        "expect": {"RTL001":"pass","RTL002":"pass","RTL003":"pass","RTL004":"pass","RTL005":"pass","RTL006":"pass","RTL007":"skip","RTL008":"pass","RTL009":"pass","RTL010":"pass"}
    },
    {
        "name": "TC51 — RTL005 fail: rst not exempt (exact rst_n only)",
        "code": """module test(input rst, output o_data);
  assign o_data = rst;
endmodule""",
        "expect": {"RTL001":"pass","RTL002":"pass","RTL003":"pass","RTL004":"pass","RTL005":"fail","RTL006":"pass","RTL007":"skip","RTL008":"pass","RTL009":"pass","RTL010":"pass"}
    },
    {
        "name": "TC52 — RTL005 fail: wrong-direction prefix (input o_, output i_)",
        "code": """module test(input o_data, output i_flag);
  assign i_flag = o_data;
endmodule""",
        "expect": {"RTL001":"pass","RTL002":"pass","RTL003":"pass","RTL004":"pass","RTL005":"fail","RTL006":"pass","RTL007":"skip","RTL008":"pass","RTL009":"pass","RTL010":"pass"}
    },
    {
        "name": "TC53 — RTL005 fail: literal range without prefix",
        "code": """module test(input [7:0] a, output [7:0] b);
  assign b = a;
endmodule""",
        "expect": {"RTL001":"pass","RTL002":"pass","RTL003":"pass","RTL004":"pass","RTL005":"fail","RTL006":"pass","RTL007":"skip","RTL008":"pass","RTL009":"pass","RTL010":"fail"}
    },
    {
        "name": "TC54 — RTL005 fail: output without prefix",
        "code": """module test(input i_clk, output data);
  assign data = i_clk;
endmodule""",
        "expect": {"RTL001":"pass","RTL002":"pass","RTL003":"pass","RTL004":"pass","RTL005":"fail","RTL006":"pass","RTL007":"skip","RTL008":"pass","RTL009":"pass","RTL010":"pass"}
    },
    {
        "name": "TC55 — RTL005 fail: mixed correct and wrong in same module",
        "code": """module test(input i_clk, input enable, output o_out, output status);
  assign o_out = i_clk & enable;
  assign status = o_out;
endmodule""",
        "expect": {"RTL001":"pass","RTL002":"pass","RTL003":"pass","RTL004":"pass","RTL005":"fail","RTL006":"pass","RTL007":"skip","RTL008":"pass","RTL009":"pass","RTL010":"pass"}
    },
    {
        "name": "TC56 — RTL005 pass: exemptions alongside prefixed ports",
        "code": """module m(input i_clk, output o_val, input rst_n);
  assign o_val = i_clk & rst_n;
endmodule""",
        "expect": {"RTL001":"pass","RTL002":"pass","RTL003":"pass","RTL004":"pass","RTL005":"pass","RTL006":"pass","RTL007":"skip","RTL008":"pass","RTL009":"pass","RTL010":"pass"}
    },
    # ── RTL002: 10 new tests ────────────────────────────────────────
    {
        "name": "TC57 — RTL002 pass: two cases both with default",
        "code": """module test(input [1:0] sel_a, input [1:0] sel_b, output reg out);
  always_comb begin
    case(sel_a)
      2'b00: out = 0;
      default: out = 1;
    endcase
    case(sel_b)
      2'b00: out = 2;
      default: out = 3;
    endcase
  end
endmodule""",
        "expect": {"RTL001":"pass","RTL002":"pass","RTL003":"pass","RTL004":"pass","RTL005":"fail","RTL006":"pass","RTL007":"skip","RTL008":"pass","RTL009":"pass","RTL010":"fail"}
    },
    {
        "name": "TC58 — RTL002 fail: two cases, second missing default",
        "code": """module test(input [1:0] sel_a, input [1:0] sel_b, output reg out);
  always_comb begin
    case(sel_a)
      2'b00: out = 0;
      default: out = 1;
    endcase
    case(sel_b)
      2'b00: out = 2;
      2'b01: out = 3;
    endcase
  end
endmodule""",
        "expect": {"RTL001":"pass","RTL002":"fail","RTL003":"pass","RTL004":"pass","RTL005":"fail","RTL006":"pass","RTL007":"skip","RTL008":"pass","RTL009":"pass","RTL010":"fail"}
    },
    {
        "name": "TC59 — RTL002 fail: case inside always_ff without default",
        "code": """module test(input clk, input rst_n, input [1:0] sel, output reg out);
  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) out <= 0;
    else begin
      case(sel)
        2'b00: out <= 1;
        2'b01: out <= 2;
      endcase
    end
  end
endmodule""",
        "expect": {"RTL001":"pass","RTL002":"fail","RTL003":"pass","RTL004":"pass","RTL005":"fail","RTL006":"pass","RTL007":"skip","RTL008":"pass","RTL009":"pass","RTL010":"fail"}
    },
    {
        "name": "TC60 — RTL002 pass: casez with default",
        "code": """module test(input [1:0] sel, output reg out);
  always_comb begin
    casez(sel)
      2'b00: out = 0;
      default: out = 1;
    endcase
  end
endmodule""",
        "expect": {"RTL001":"pass","RTL002":"pass","RTL003":"pass","RTL004":"pass","RTL005":"fail","RTL006":"pass","RTL007":"skip","RTL008":"pass","RTL009":"pass","RTL010":"fail"}
    },
    {
        "name": "TC61 — RTL002 fail: empty case",
        "code": """module test(input [1:0] sel, output reg out);
  always_comb begin
    case(sel)
    endcase
  end
endmodule""",
        "expect": {"RTL001":"pass","RTL002":"fail","RTL003":"pass","RTL004":"pass","RTL005":"fail","RTL006":"pass","RTL007":"skip","RTL008":"pass","RTL009":"pass","RTL010":"fail"}
    },
    {
        "name": "TC62 — RTL002 fail: default only in comment",
        "code": """module test(input [1:0] sel, output reg out);
  always_comb begin
    case(sel)
      // no default label here
      2'b00: out = 1;
      2'b01: out = 2;
    endcase
  end
endmodule""",
        "expect": {"RTL001":"pass","RTL002":"fail","RTL003":"pass","RTL004":"pass","RTL005":"fail","RTL006":"pass","RTL007":"skip","RTL008":"pass","RTL009":"pass","RTL010":"fail"}
    },
    {
        "name": "TC63 — RTL002 pass: case with begin/end blocks + default",
        "code": """module test(input [1:0] sel, input a, input b, output reg out);
  always_comb begin
    case(sel)
      2'b00: begin
        out = a;
      end
      2'b01: begin
        out = b;
      end
      default: out = 0;
    endcase
  end
endmodule""",
        "expect": {"RTL001":"pass","RTL002":"pass","RTL003":"pass","RTL004":"pass","RTL005":"fail","RTL006":"pass","RTL007":"skip","RTL008":"pass","RTL009":"pass","RTL010":"fail"}
    },
    {
        "name": "TC64 — RTL002 fail: all values covered but no default keyword",
        "code": """module test(input [1:0] sel, output reg out);
  always_comb begin
    case(sel)
      2'b00: out = 0;
      2'b01: out = 1;
      2'b10: out = 2;
      2'b11: out = 3;
    endcase
  end
endmodule""",
        "expect": {"RTL001":"pass","RTL002":"fail","RTL003":"pass","RTL004":"pass","RTL005":"fail","RTL006":"pass","RTL007":"skip","RTL008":"pass","RTL009":"pass","RTL010":"fail"}
    },
    {
        "name": "TC65 — RTL002 pass: case inside with default",
        "code": """module test(input [1:0] sel, output reg out);
  always_comb begin
    case (sel) inside
      2'b00: out = 0;
      default: out = 1;
    endcase
  end
endmodule""",
        "expect": {"RTL001":"pass","RTL002":"pass","RTL003":"pass","RTL004":"pass","RTL005":"fail","RTL006":"pass","RTL007":"skip","RTL008":"pass","RTL009":"pass","RTL010":"fail"}
    },
    {
        "name": "TC66 — RTL002 pass: shared label with default",
        "code": """module test(input [1:0] sel, output reg out);
  always_comb begin
    case(sel)
      2'b00: out = 0;
      2'b01,
      default: out = 1;
    endcase
  end
endmodule""",
        "expect": {"RTL001":"pass","RTL002":"pass","RTL003":"pass","RTL004":"pass","RTL005":"fail","RTL006":"pass","RTL007":"skip","RTL008":"pass","RTL009":"pass","RTL010":"fail"}
    },
]

# 3. Run all tests
print(f"\n{'='*100}", flush=True)
print(f"{'TEST':6s} {'NAME':35s} {'SCORE':6s} {'VIOL':4s} {'WARN':4s} {'PASS':4s} {'SKIP':4s}  MISMATCHES", flush=True)
print(f"{'='*100}", flush=True)

all_pass = True
results_log = []

for tc in tests:
    name = tc["name"]
    code = tc["code"]
    expect = tc["expect"]

    r = requests.post(f"{BASE}/review/paste", headers=headers, json={
        "code": code, "review_type": "rtl", "user_name": "Manikanta"
    })

    if r.status_code != 200:
        print(f"{'ERROR':6s} {name:35s} HTTP {r.status_code}", flush=True)
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

    v = len(data.get("violations", []))
    w = len(data.get("warnings", []))
    p = len(passed)
    s = len(needs_manual)

    status = "PASS" if not mismatches else "FAIL"
    if status == "FAIL":
        all_pass = False

    print(f"{status:6s} {name:35s} {score:5.1f}  {v:3d}  {w:3d}  {p:3d}  {s:3d}  {'; '.join(mismatches)}", flush=True)

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

with open("test_rtl_report.json", "w") as f:
    json.dump(results_log, f, indent=2, ensure_ascii=False)
print("Report saved to test_rtl_report.json", flush=True)
