import re

_REGISTRY = {}


def register(review_type, rule_id):
    def wrapper(fn):
        _REGISTRY.setdefault(review_type, {})[rule_id] = fn
        return fn
    return wrapper


def run_static_checks(code: str, review_type: str) -> dict[str, dict]:
    results = {}
    for rule_id, check_fn in _REGISTRY.get(review_type, {}).items():
        try:
            result = check_fn(code)
            if result is not None:
                results[rule_id] = result
        except Exception:
            pass
    return results


def get_static_rule_ids(review_type: str) -> set[str]:
    return set(_REGISTRY.get(review_type, {}).keys())


# ──────────────────────────────── RTL ────────────────────────────────

@register("rtl", "RTL001")
def _check_rtl001(code):
    """No latches — every always_ff/always_comb/always block must have complete assignments in all branches."""
    # Match all always block types:
    #   always_ff @(...)
    #   always_comb
    #   always_latch
    #   always @(posedge|negedge ...) — sequential
    #   always @(*)            — combinational
    #   always @ (...)         — could be either; flag anything not sequential
    for m in re.finditer(
        r"\balways_ff\b|\balways_comb\b|\balways_latch\b|\balways\s*@\s*\([^)]*\)",
        code
    ):
        block_start = m.start()
        rest = code[block_start:]
        depth = 0
        in_block = False
        end_pos = len(rest)
        for j in range(len(rest)):
            if rest[j:j+5] == "begin":
                depth += 1
                in_block = True
            if rest[j:j+3] == "end":
                depth -= 1
                if depth == 0 and in_block:
                    end_pos = j + 3
                    break
            if not in_block and rest[j] == ";":
                end_pos = j + 1
                break
        block = rest[:end_pos]
        if_count = len(re.findall(r"\bif\b", block))
        else_count = len(re.findall(r"\belse\b", block))
        if if_count > else_count:
            line_num = code[:block_start].count("\n") + 1
            return {"result": "fail", "severity": "violation",
                    "evidence": f"always block at line {line_num} has {if_count} if(s) but only {else_count} else(s) — incomplete branching may infer latches",
                    "line": line_num}
    return {"result": "pass", "severity": "violation",
            "evidence": "all always blocks have complete branch coverage", "line": "N/A"}


@register("rtl", "RTL002")
def _check_rtl002(code):
    """All case/casex/casez statements must have a default branch."""
    violations = []
    depth = 0
    lines = code.split("\n")
    case_start = None
    for i, line in enumerate(lines):
        stripped = line.strip()
        if re.match(r"\b(case|casex|casez)\b\s*\(", stripped, re.IGNORECASE):
            if depth == 0:
                case_start = i
            depth += 1
        if stripped.startswith("endcase"):
            if depth == 1 and case_start is not None:
                block = "\n".join(lines[case_start:i+1])
                if not re.search(r"\bdefault\b\s*:", block):
                    violations.append(i+1)
            depth = max(0, depth - 1)
            if depth == 0:
                case_start = None
    if violations:
        return {"result": "fail", "severity": "violation",
                "evidence": f"case statement(s) at line(s) {violations} missing default branch",
                "line": violations[0]}
    return {"result": "pass", "severity": "violation",
            "evidence": "all case statements have a default branch", "line": "N/A"}


@register("rtl", "RTL003")
def _check_rtl003(code):
    """Reset must be asynchronous and active-low (negedge rst_n)."""
    m = re.search(r"always_ff\s*@\s*\([^)]*negedge\s+(\w*(?:rst|reset)\w*)", code, re.IGNORECASE)
    if m:
        reset_sig = m.group(1)
        return {"result": "pass", "severity": "violation",
                "evidence": f"active-low async reset (negedge {reset_sig}) found in sensitivity list",
                "line": "N/A"}
    if re.search(r"always_ff\s*@\s*\(", code):
        return {"result": "fail", "severity": "violation",
                "evidence": "no negedge reset signal found in always_ff sensitivity list",
                "line": "N/A"}
    return {"result": "pass", "severity": "violation",
            "evidence": "no sequential always_ff block to check", "line": "N/A"}


@register("rtl", "RTL004")
def _check_rtl004(code):
    """Use always_ff/always_comb, not plain always."""
    matches = list(re.finditer(r"\balways\b(?!_ff|_comb|_latch)\s*@", code))
    if matches:
        lines = [code[:m.start()].count("\n") + 1 for m in matches]
        return {"result": "fail", "severity": "violation",
                "evidence": f"plain 'always @' found at line(s) {lines} — use always_ff or always_comb",
                "line": lines[0]}
    return {"result": "pass", "severity": "violation",
            "evidence": "no plain 'always' blocks found", "line": "N/A"}


@register("rtl", "RTL005")
def _check_rtl005(code):
    """Port names must follow i_ prefix for inputs, o_ prefix for outputs."""
    violations = []
    for m in re.finditer(r"\b(input|output)\s+(?:(?:logic|wire|reg|bit)\s+)?(?:\[[^]]*\]\s+)?(\w+)", code):
        direction = m.group(1)
        name = m.group(2)
        prefix = "i_" if direction == "input" else "o_"
        if not name.startswith(prefix) and name not in ("clk", "rst_n"):
            line = code[:m.start()].count("\n") + 1
            violations.append((line, name, direction, prefix))
    if violations:
        details = "; ".join(f"line {l}: {n} ({d}) should start with {p}" for l, n, d, p in violations)
        return {"result": "fail", "severity": "warning",
                "evidence": details, "line": violations[0][0]}
    return {"result": "pass", "severity": "warning",
            "evidence": "all port names follow i_/o_ prefix convention", "line": "N/A"}


@register("rtl", "RTL008")
def _check_rtl008(code):
    """No unused signals or ports — simple identifier usage counting."""
    declarations = set()
    decl_positions = set()
    for m in re.finditer(r"\b(input|output|wire|reg|logic)\s+(?:\[[^]]*\])?\s*(\w+)", code):
        name = m.group(2)
        declarations.add(name)
        # mark the declaration word's position range
        for p in range(m.start(2), m.end(2)):
            decl_positions.add(p)
    usages = set()
    for m in re.finditer(r"\b(\w+)\b", code):
        # skip if this match falls inside a declaration
        if any(p in decl_positions for p in range(m.start(1), m.end(1))):
            continue
        usages.add(m.group(1))
    builtins = {"input", "output", "wire", "reg", "logic", "rst_n", "clk", "posedge",
                "negedge", "module", "endmodule", "always", "always_ff", "always_comb",
                "assign", "case", "endcase", "default", "if", "else", "for", "begin",
                "end", "parameter", "localparam"}
    unused = declarations - usages - builtins
    if unused:
        return {"result": "fail", "severity": "warning",
                "evidence": f"potentially unused signals: {', '.join(sorted(unused))}",
                "line": "N/A"}
    return {"result": "pass", "severity": "warning",
            "evidence": "no unused signals detected", "line": "N/A"}


@register("rtl", "RTL009")
def _check_rtl009(code):
    """Module name must match filename."""
    m_mod = re.search(r"\bmodule\s+(\w+)", code)
    if not m_mod:
        return {"result": "fail", "severity": "warning",
                "evidence": "no module declaration found", "line": "N/A"}
    mod_name = m_mod.group(1)
    m_file = re.search(r"###\s*(?:.*[/\\])?(\w+)\.\w+", code)
    if m_file:
        file_stem = m_file.group(1)
        if mod_name.lower() == file_stem.lower():
            return {"result": "pass", "severity": "warning",
                    "evidence": f"module name '{mod_name}' matches filename stem '{file_stem}'",
                    "line": "N/A"}
        return {"result": "fail", "severity": "warning",
                "evidence": f"module name '{mod_name}' does not match filename stem '{file_stem}'",
                "line": "N/A"}
    return {"result": "pass", "severity": "warning",
            "evidence": "unable to verify without filename context — paste flow assumed",
            "line": "N/A"}


@register("rtl", "RTL010")
def _check_rtl010(code):
    """Parameters must be used for widths — no hardcoded numbers in port declarations."""
    violations = []
    for m in re.finditer(r"\b(input|output)\s+(?:logic|wire|reg|bit)?\s*\[(\d+):(\d+)\]", code):
        lo, hi = int(m.group(2)), int(m.group(3))
        if lo > 0 or hi > 0:
            line = code[:m.start()].count("\n") + 1
            violations.append(line)
    if violations:
        return {"result": "fail", "severity": "warning",
                "evidence": f"hardcoded bit-width literals in port declarations at line(s) {violations} — use parameters",
                "line": violations[0]}
    return {"result": "pass", "severity": "warning",
            "evidence": "no hardcoded bit-width literals in port declarations", "line": "N/A"}


@register("rtl", "RTL006")
def _check_rtl006(code):
    """No X assignments — all signals must have a defined reset state."""
    matches = list(re.finditer(r"=\s*'[xX]|=\s*\d+'[bhodBOD]?\s*[xX]", code))
    if matches:
        lines = [code[:m.start()].count("\n") + 1 for m in matches]
        return {"result": "fail", "severity": "violation",
                "evidence": f"X assignments found at line(s) {lines} — use defined reset values instead of x",
                "line": lines[0]}
    return {"result": "pass", "severity": "violation",
            "evidence": "no X assignments found", "line": "N/A"}


# ──────────────────────────────── SV ────────────────────────────────

@register("sv", "SV001")
def _check_sv001(code):
    """No hardcoded delays (#100, #50 etc.) — use clock-based waiting only."""
    matches = list(re.finditer(r"#\d+", code))
    if matches:
        lines = [code[:m.start()].count("\n") + 1 for m in matches]
        return {"result": "fail", "severity": "violation",
                "evidence": f"hardcoded delays found at line(s) {lines}",
                "line": lines[0]}
    return {"result": "pass", "severity": "violation",
            "evidence": "no hardcoded delays found", "line": "N/A"}


@register("sv", "SV002")
def _check_sv002(code):
    """Clock must be generated using always block with a parameter for period."""
    has_clock_gen = re.search(r"\b(always|initial)\b", code)
    if not has_clock_gen:
        return {"result": "pass", "severity": "violation",
                "evidence": "no clock generation block found — skip", "line": "N/A"}
    has_param_period = re.search(r"(parameter|localparam)\s+\w*\s*period", code, re.IGNORECASE)
    if has_param_period:
        return {"result": "pass", "severity": "violation",
                "evidence": "clock period is parameterized", "line": "N/A"}
    return {"result": "fail", "severity": "violation",
            "evidence": "clock period is not parameterized — use a parameter for the period",
            "line": "N/A"}


@register("sv", "SV005")
def _check_sv005(code):
    """All inputs must be driven with non-blocking assignments synchronized to clock edge."""
    blocking_inputs = list(re.finditer(r"@\([^)]*posedge\s+\w+[^)]*\)[^;]*\n[^;]*\b(\w+)\s*=", code))
    if blocking_inputs:
        lines = [code[:m.start()].count("\n") + 1 for m in blocking_inputs]
        return {"result": "fail", "severity": "violation",
                "evidence": f"blocking assignments (=) to signals inside clock edge block at line(s) {lines} — use <=",
                "line": lines[0]}
    return {"result": "pass", "severity": "violation",
            "evidence": "no blocking assignments to inputs in clock edge blocks", "line": "N/A"}


@register("sv", "SV006")
def _check_sv006(code):
    """Test must have a timeout watchdog."""
    has_timeout = re.search(r"#\d+\s+.*\$finish", code) or re.search(r"fork[^`]*#\d+\s+.*disable\s+fork", code)
    if has_timeout:
        return {"result": "pass", "severity": "violation",
                "evidence": "timeout watchdog pattern found", "line": "N/A"}
    return {"result": "fail", "severity": "violation",
            "evidence": "no timeout watchdog found — simulation could run forever",
            "line": "N/A"}


@register("sv", "SV007")
def _check_sv007(code):
    """Use $display/$monitor with timestamps."""
    has_display = re.search(r"\$display|\$monitor", code)
    if not has_display:
        return {"result": "fail", "severity": "warning",
                "evidence": "no $display or $monitor found — use for debugging", "line": "N/A"}
    has_time = re.search(r"\$(display|monitor)[^;]*\$time", code)
    if has_time:
        return {"result": "pass", "severity": "warning",
                "evidence": "$display/$monitor includes $time timestamp", "line": "N/A"}
    return {"result": "fail", "severity": "warning",
            "evidence": "$display/$monitor found but without $time timestamp", "line": "N/A"}


@register("sv", "SV008")
def _check_sv008(code):
    """File name must follow format: <module_name>_tb.sv."""
    m_file = re.search(r"###\s*(?:.*[/\\])?(\w+)_tb\.sv", code)
    if m_file:
        return {"result": "pass", "severity": "warning",
                "evidence": "filename matches <module>_tb.sv pattern", "line": "N/A"}
    m_any = re.search(r"###\s*(?:.*[/\\])?(\w+)\.\w+", code)
    if m_any:
        return {"result": "fail", "severity": "warning",
                "evidence": "filename does not follow <module>_tb.sv pattern", "line": "N/A"}
    return {"result": "pass", "severity": "warning",
            "evidence": "unable to verify without filename context — paste flow assumed", "line": "N/A"}


@register("sv", "SV010")
def _check_sv010(code):
    """No $finish without printing a PASS or FAIL message."""
    lines = code.split("\n")
    for i, line in enumerate(lines):
        if "$finish" in line:
            window = "\n".join(lines[max(0, i-10):i])
            if not re.search(r'\$display\([^)]*"(?:PASS|FAIL)', window, re.IGNORECASE):
                return {"result": "fail", "severity": "violation",
                        "evidence": f"$finish at line {i+1} without preceding PASS/FAIL $display",
                        "line": i+1}
    return {"result": "pass", "severity": "violation",
            "evidence": "all $finish calls have PASS/FAIL messages", "line": "N/A"}


# ──────────────────────────────── UVM ────────────────────────────────

@register("uvm", "UVM001")
def _check_uvm001(code):
    """Use `uvm_info/warning/error macros, never uvm_report_* directly."""
    matches = list(re.finditer(r"\buvm_report_(info|warning|error)\b", code))
    if matches:
        lines = [code[:m.start()].count("\n") + 1 for m in matches]
        return {"result": "fail", "severity": "violation",
                "evidence": f"direct uvm_report_* calls at line(s) {lines} — use `uvm_info/warning/error macros",
                "line": lines[0]}
    return {"result": "pass", "severity": "violation",
            "evidence": "no direct uvm_report_* calls — macros used correctly", "line": "N/A"}


@register("uvm", "UVM002")
def _check_uvm002(code):
    """All components must use `uvm_component_utils."""
    for m in re.finditer(r"\bclass\s+(\w+)\s+extends\s+(?:uvm_component|uvm_driver|uvm_monitor|uvm_agent|uvm_env|uvm_test|uvm_scoreboard|uvm_subscriber|uvm_sequencer)\b", code):
        class_name = m.group(1)
        if not re.search(r"`uvm_component_utils\s*\(\s*" + re.escape(class_name) + r"\s*\)", code):
            line = code[:m.start()].count("\n") + 1
            return {"result": "fail", "severity": "violation",
                    "evidence": f"class '{class_name}' at line {line} extends uvm_component but missing `uvm_component_utils({class_name})",
                    "line": line}
    return {"result": "pass", "severity": "violation",
            "evidence": "all uvm_component classes have `uvm_component_utils", "line": "N/A"}


@register("uvm", "UVM003")
def _check_uvm003(code):
    """All sequence items must use `uvm_object_utils."""
    for m in re.finditer(r"\bclass\s+(\w+)\s+extends\s+(uvm_sequence_item|uvm_object|uvm_sequence)\b", code):
        class_name = m.group(1)
        if not re.search(r"`uvm_object_utils\s*\(\s*" + re.escape(class_name) + r"\s*\)", code):
            line = code[:m.start()].count("\n") + 1
            return {"result": "fail", "severity": "violation",
                    "evidence": f"class '{class_name}' at line {line} extends {m.group(2)} but missing `uvm_object_utils({class_name})",
                    "line": line}
    return {"result": "pass", "severity": "violation",
            "evidence": "all sequence_item/object classes have `uvm_object_utils", "line": "N/A"}


@register("uvm", "UVM004")
def _check_uvm004(code):
    """Driver must use get_next_item / item_done handshake."""
    driver_body = re.search(r"class\s+\w+\s+extends\s+uvm_driver\b.*?endclass", code, re.DOTALL)
    if not driver_body:
        return {"result": "pass", "severity": "violation",
                "evidence": "no uvm_driver class found — skip", "line": "N/A"}
    body = driver_body.group(0)
    has_get_next = "get_next_item" in body
    has_item_done = "item_done" in body
    if has_get_next and has_item_done:
        return {"result": "pass", "severity": "violation",
                "evidence": "driver uses get_next_item / item_done handshake", "line": "N/A"}
    missing = []
    if not has_get_next:
        missing.append("get_next_item")
    if not has_item_done:
        missing.append("item_done")
    return {"result": "fail", "severity": "violation",
            "evidence": f"driver missing: {', '.join(missing)}", "line": "N/A"}


@register("uvm", "UVM007")
def _check_uvm007(code):
    """Factory overrides must be used — no hardcoded type names in env."""
    env_body = re.search(r"class\s+\w+\s+extends\s+uvm_env\b.*?endclass", code, re.DOTALL)
    if not env_body:
        return {"result": "pass", "severity": "warning",
                "evidence": "no uvm_env class found — skip", "line": "N/A"}
    body = env_body.group(0)
    if re.search(r"::type_id::create\s*\(", body):
        return {"result": "pass", "severity": "warning",
                "evidence": "factory create() used correctly", "line": "N/A"}
    new_calls = list(re.finditer(r"=\s*\w+::new\s*\(", body))
    if new_calls:
        lns = [body[:m.start()].count("\n") + 1 for m in new_calls]
        return {"result": "fail", "severity": "warning",
                "evidence": f"direct ::new() calls at line(s) {lns} — use type_id::create() for factory override support",
                "line": lns[0]}
    if re.search(r"=\s*new\s*\(", body):
        return {"result": "fail", "severity": "warning",
                "evidence": "direct new() found — use type_id::create() for factory override support",
                "line": "N/A"}
    return {"result": "pass", "severity": "warning",
            "evidence": "no factory override issues detected in env", "line": "N/A"}


@register("uvm", "UVM005")
def _check_uvm005(code):
    """No hardcoded delays in driver."""
    driver_body = re.search(r"class\s+\w+\s+extends\s+uvm_driver\b.*?endclass", code, re.DOTALL)
    if not driver_body:
        return {"result": "pass", "severity": "violation",
                "evidence": "no uvm_driver class found", "line": "N/A"}
    matches = list(re.finditer(r"#\d+", driver_body.group(0)))
    if matches:
        return {"result": "fail", "severity": "violation",
                "evidence": "hardcoded delays (#\\d+) found inside driver class",
                "line": "N/A"}
    return {"result": "pass", "severity": "violation",
            "evidence": "no hardcoded delays in driver", "line": "N/A"}


@register("uvm", "UVM009")
def _check_uvm009(code):
    """All phases must call super.<phase_name>()."""
    violations = []
    for m in re.finditer(r"\b(function|task)\s+(?:void\s+)?(\w+)_phase\s*\(", code):
        phase_name = m.group(2)
        line = code[:m.start()].count("\n") + 1
        body_start = m.end()
        body_end = code.find("end" + ("task" if m.group(1) == "task" else "function"), body_start)
        body = code[body_start:body_end] if body_end > body_start else ""
        if f"super.{phase_name}_phase(" not in body:
            violations.append((line, phase_name))
    if violations:
        details = "; ".join(f"line {l}: {p}_phase missing super.{p}_phase()" for l, p in violations)
        return {"result": "fail", "severity": "violation",
                "evidence": details, "line": violations[0][0]}
    return {"result": "pass", "severity": "violation",
            "evidence": "all phases call super.<phase_name>()", "line": "N/A"}


@register("uvm", "UVM010")
def _check_uvm010(code):
    """Objection must be raised in pre_start and dropped in post_start."""
    has_pre_start = re.search(r"\bfunction\s+void\s+pre_start\b", code)
    has_post_start = re.search(r"\bfunction\s+void\s+post_start\b", code)

    if has_pre_start:
        pre_body = code[has_pre_start.end():]
        end_idx = pre_body.find("\nendfunction")
        pre_body = pre_body[:end_idx] if end_idx > 0 else pre_body
        if "raise_objection" not in pre_body:
            return {"result": "fail", "severity": "violation",
                    "evidence": "pre_start found but missing raise_objection", "line": "N/A"}

    if has_post_start:
        post_body = code[has_post_start.end():]
        end_idx = post_body.find("\nendfunction")
        post_body = post_body[:end_idx] if end_idx > 0 else post_body
        if "drop_objection" not in post_body:
            return {"result": "fail", "severity": "violation",
                    "evidence": "post_start found but missing drop_objection", "line": "N/A"}

    if has_pre_start and has_post_start:
        return {"result": "pass", "severity": "violation",
                "evidence": "objection raised in pre_start and dropped in post_start", "line": "N/A"}
    if not has_pre_start and not has_post_start:
        return {"result": "fail", "severity": "violation",
                "evidence": "missing both pre_start and post_start functions for objection handling",
                "line": "N/A"}
    missing = []
    if not has_pre_start:
        missing.append("pre_start")
    if not has_post_start:
        missing.append("post_start")
    return {"result": "fail", "severity": "violation",
            "evidence": f"missing: {', '.join(missing)} for objection handling", "line": "N/A"}


# ──────────────────────────────── Verilog TB ────────────────────────────────

@register("verilog_tb", "TB001")
def _check_tb001(code):
    """Module must have no ports — testbench is top-level."""
    m = re.search(r"\bmodule\s+\w+\s*\((.*?)\)", code, re.DOTALL)
    if m:
        ports = m.group(1).strip()
        if ports and ports != ";":
            line = code[:m.start()].count("\n") + 1
            return {"result": "fail", "severity": "violation",
                    "evidence": f"module at line {line} has ports — testbench should have no I/O ports",
                    "line": line}
    return {"result": "pass", "severity": "violation",
            "evidence": "module has no ports (correct for testbench)", "line": "N/A"}


@register("verilog_tb", "TB002")
def _check_tb002(code):
    """DUT must be instantiated with named port connections."""
    for m in re.finditer(r"\w+\s+#\s*\(.*?\)\s+(\w+)\s*\(.*?\)\s*;", code, re.DOTALL):
        inst_body = m.group(0)
        if re.search(r"\.\w+\s*\(", inst_body):
            continue
        line = code[:m.start()].count("\n") + 1
        return {"result": "fail", "severity": "violation",
                "evidence": f"instantiation at line {line} appears to use positional connections — use .port(signal) style",
                "line": line}
    return {"result": "pass", "severity": "violation",
            "evidence": "all instantiations use named port connections", "line": "N/A"}


@register("verilog_tb", "TB003")
def _check_tb003(code):
    """Clock must be generated using an initial/always block with a parameterized period."""
    has_clock_gen = re.search(r"\b(always|initial)\b", code)
    if not has_clock_gen:
        return {"result": "pass", "severity": "violation",
                "evidence": "no clock generation block found — skip", "line": "N/A"}
    has_param_period = re.search(r"(parameter|localparam)\s+\w*\s*period", code, re.IGNORECASE)
    if has_param_period:
        return {"result": "pass", "severity": "violation",
                "evidence": "clock period is parameterized", "line": "N/A"}
    return {"result": "fail", "severity": "violation",
            "evidence": "clock period is not parameterized — use a parameter for the period",
            "line": "N/A"}


@register("verilog_tb", "TB005")
def _check_tb005(code):
    """All DUT inputs must be declared as reg type, outputs as wire type."""
    m_dut = re.search(r"\w+\s+(?:#\s*\([^)]*\)\s+)?\w+\s*\(", code)
    if m_dut and m_dut.group().split()[0] == "module":
        m_dut = None
    if not m_dut:
        return {"result": "pass", "severity": "violation",
                "evidence": "no DUT instantiation found", "line": "N/A"}
    has_reg = re.search(r"\breg\b", code)
    has_wire = re.search(r"\bwire\b", code)
    if has_reg and has_wire:
        return {"result": "pass", "severity": "violation",
                "evidence": "both reg and wire declarations present", "line": "N/A"}
    missing = []
    if not has_reg:
        missing.append("reg")
    if not has_wire:
        missing.append("wire")
    return {"result": "fail", "severity": "violation",
            "evidence": f"missing declaration types: {', '.join(missing)} — DUT inputs should be reg, outputs wire",
            "line": "N/A"}


@register("verilog_tb", "TB006")
def _check_tb006(code):
    """Simulation must have a timeout watchdog."""
    has_timeout = re.search(r"#\d+\s+.*\$finish", code) or re.search(r"fork[^`]*#\d+\s+.*disable\s+fork", code)
    if has_timeout:
        return {"result": "pass", "severity": "violation",
                "evidence": "timeout watchdog pattern found", "line": "N/A"}
    return {"result": "fail", "severity": "violation",
            "evidence": "no timeout watchdog found — simulation could run forever",
            "line": "N/A"}


@register("verilog_tb", "TB007")
def _check_tb007(code):
    """Use $monitor or $display with timestamps."""
    has_display = re.search(r"\$display|\$monitor", code)
    if not has_display:
        return {"result": "fail", "severity": "warning",
                "evidence": "no $display or $monitor found — use for debugging", "line": "N/A"}
    has_time = re.search(r"\$(display|monitor)[^;]*\$time", code)
    if has_time:
        return {"result": "pass", "severity": "warning",
                "evidence": "$display/$monitor includes $time timestamp", "line": "N/A"}
    return {"result": "fail", "severity": "warning",
            "evidence": "$display/$monitor found but without $time timestamp", "line": "N/A"}


@register("verilog_tb", "TB008")
def _check_tb008(code):
    """Use $finish with a PASS/FAIL message."""
    lines = code.split("\n")
    for i, line in enumerate(lines):
        if "$finish" in line:
            window = "\n".join(lines[max(0, i-10):i])
            if not re.search(r'\$display\([^)]*"(?:PASS|FAIL)', window, re.IGNORECASE):
                return {"result": "fail", "severity": "warning",
                        "evidence": f"$finish at line {i+1} without preceding PASS/FAIL $display",
                        "line": i+1}
    return {"result": "pass", "severity": "warning",
            "evidence": "all $finish calls have PASS/FAIL messages", "line": "N/A"}


@register("verilog_tb", "TB010")
def _check_tb010(code):
    """File name should follow format: tb_<module_name>.v."""
    m_file = re.search(r"###\s*(?:.*[/\\])?tb_(\w+)\.\w+", code)
    if m_file:
        return {"result": "pass", "severity": "warning",
                "evidence": "filename follows tb_<module>.v pattern", "line": "N/A"}
    m_any = re.search(r"###\s*(?:.*[/\\])?(\w+)\.\w+", code)
    if m_any:
        return {"result": "fail", "severity": "warning",
                "evidence": "filename does not follow tb_<module>.v pattern", "line": "N/A"}
    return {"result": "pass", "severity": "warning",
            "evidence": "unable to verify without filename context — paste flow assumed", "line": "N/A"}
