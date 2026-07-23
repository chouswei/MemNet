"""Extract SCPI commands from RTO User Manual PDF into MemNet @CMD rows."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PDF = ROOT / "data" / "rto" / "UserManual_en_29.pdf"
OUT_CMD = ROOT / "data" / "rto" / "scpi_commands.txt"
OUT_WIRE = ROOT / "parts" / "common" / "memnet" / "memnet" / "examples" / "workflow.rto-remote.example.txt"

LIST_FIRST_PAGE = 2955
LIST_LAST_PAGE = 3058

LIST_LINE = re.compile(
    r"^(\*?[A-Za-z][A-Za-z0-9:<>[\],]+?\??)\s*\.+\s*(\d+)\s*$"
)

# First SCPI token (after optional leading colon) -> @SEC id
ROOT_TO_SEC: dict[str, str] = {
    "ACQuire": "S_acq_remote",
    "TRIGger": "S_trig_remote",
    "MEASurement": "S_meas_remote",
    "CHANnel": "S_chan_remote",
    "TIMebase": "S_tbase_remote",
    "WAVeform": "S_wave_read",
    "SYSTem": "S_cmd_syst",
    "DISPlay": "S_disp_remote",
    "FORMat": "S_form_remote",
    "HISTogram": "S_hist_remote",
    "MARKer": "S_mark_remote",
    "MATH": "S_math_remote",
    "MMEMory": "S_file_remote",
    "HCOPy": "S_file_remote",
    "CALCulate": "S_math_remote",
    "CURSor": "S_mark_remote",
    "SEARch": "S_search_remote",
    "BUS": "S_bus_remote",
    "POWer": "S_power_remote",
    "STATus": "S_status_remote",
    "WGENerator": "S_wgen_remote",
    "PROBe": "S_probe_remote",
    "LAYout": "S_disp_remote",
    "REFLevel": "S_ref_remote",
    "REFCurve": "S_ref_remote",
    "EXPort": "S_export_remote",
    "DEEMbedding": "S_deembed_remote",
    "ZVC": "S_zvc_remote",
    "ADVJitter": "S_app_jitter",
    "LANE": "S_app_lane",
    "MTESt": "S_app_mtest",
    "EYE": "S_app_eye",
    "WGEN": "S_wgen_remote",
    "CDR": "S_app_cdr",
    "TDRT": "S_app_tdrt",
    "DIFFerential": "S_app_diff",
    "DIAGnostic": "S_trace_remote",
    "IQ": "S_app_iq",
    "PGENerator": "S_wgen_remote",
    "REPort": "S_export_remote",
    "CALibration": "S_cmd_syst",
    "DIGital": "S_chan_remote",
    "GENerator": "S_wgen_remote",
    "PSRC": "S_power_remote",
    "SIGNalconfig": "S_sigcfg_remote",
    "USRDefined": "S_cmd_general",
    "RUN": "S_acq_remote",
    "STOP": "S_acq_remote",
    "ABORt": "S_acq_remote",
}


def pdftotext_list_section() -> str:
    cmd = [
        "pdftotext",
        "-f",
        str(LIST_FIRST_PAGE),
        "-l",
        str(LIST_LAST_PAGE),
        str(PDF),
        "-",
    ]
    return subprocess.check_output(cmd, text=True, encoding="utf-8", errors="replace")


def normalize_scpi(header: str) -> str:
    h = header.strip()
    if h.startswith("*"):
        return h
    if not h.startswith(":"):
        h = ":" + h
    return h


def root_token(scpi: str) -> str:
    if scpi.startswith("*"):
        return "*"
    body = scpi.lstrip(":")
    token = body.split(":")[0]
    token = re.sub(r"<[^>]+>.*", "", token)
    token = re.sub(r"\[.*", "", token)
    return token


def subsystem_from_scpi(scpi: str) -> str:
    if scpi.startswith("*"):
        return "S_cmd_common"
    root = root_token(scpi)
    if root in ROOT_TO_SEC:
        return ROOT_TO_SEC[root]
    # prefix match for roots with suffix like CHANnel<ch>
    for key, sec in ROOT_TO_SEC.items():
        if root.startswith(key):
            return sec
    return "S_cmd_misc"


def role_from_scpi(scpi: str) -> str:
    return "query" if scpi.rstrip().endswith("?") else "set"


def slug_from_scpi(scpi: str, used: set[str]) -> str:
    base = scpi.strip().rstrip("?")
    base = re.sub(r"^[*:]", "", base)
    base = re.sub(r"[^A-Za-z0-9]+", "_", base)
    base = re.sub(r"_+", "_", base).strip("_").lower()
    if not base:
        base = "cmd"
    if len(base) > 44:
        base = base[:44]
    slug = base
    n = 2
    while slug in used:
        slug = f"{base}_{n}"
        n += 1
    used.add(slug)
    return slug


def extract_list_of_commands(text: str) -> list[tuple[str, int]]:
    found: list[tuple[str, int]] = []
    seen: set[str] = set()
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("R&S") or line.startswith("User Manual"):
            continue
        m = LIST_LINE.match(line)
        if not m:
            continue
        scpi = normalize_scpi(m.group(1))
        page = int(m.group(2))
        key = scpi.upper()
        if key in seen:
            continue
        seen.add(key)
        found.append((scpi, page))
    return found


def params_code_from_scpi(scpi: str) -> str:
    if "<" in scpi or "[" in scpi:
        return "indexed"
    return "-"


def build_wire_prefix() -> str:
    secs = [
        ("S_rc_intro", "Remote control intro", "13", "-", "1"),
        ("S_net_lan", "Network and LAN", "13.2", "S_rc_intro", "2"),
        ("S_scpi_basics", "SCPI basics", "14.1", "-", "3"),
        ("S_cmd_common", "Common commands", "26.5", "-", "4"),
        ("S_cmd_general", "General remote settings", "26.6", "-", "5"),
        ("S_cmd_syst", "SYSTem commands", "26.6", "-", "6"),
        ("S_acq_remote", "ACQuire remote", "26.7", "-", "7"),
        ("S_trig_remote", "TRIGger remote", "26.8", "-", "8"),
        ("S_meas_remote", "MEASurement remote", "26.9", "-", "9"),
        ("S_chan_remote", "CHANnel setup", "26.10", "-", "10"),
        ("S_tbase_remote", "TIMebase setup", "26.11", "-", "11"),
        ("S_wave_read", "WAVeform read", "26.12", "-", "12"),
        ("S_disp_remote", "DISPlay remote", "26.13", "-", "13"),
        ("S_form_remote", "FORMat remote", "26.14", "-", "14"),
        ("S_hist_remote", "HISTogram remote", "26.15", "-", "15"),
        ("S_mark_remote", "MARKer and CURSor", "26.16", "-", "16"),
        ("S_math_remote", "MATH and CALCulate", "26.17", "-", "17"),
        ("S_file_remote", "MMEMory and HCOPy", "26.18", "-", "18"),
        ("S_search_remote", "SEARch and protocol decode", "26.19", "-", "19"),
        ("S_bus_remote", "BUS remote", "26.20", "-", "20"),
        ("S_power_remote", "POWer remote", "26.21", "-", "21"),
        ("S_status_remote", "STATus remote", "26.22", "-", "22"),
        ("S_wgen_remote", "WGENerator remote", "26.23", "-", "23"),
        ("S_probe_remote", "PROBe remote", "26.24", "-", "24"),
        ("S_ref_remote", "REFLevel and REFCurve", "26.25", "-", "25"),
        ("S_export_remote", "EXPort and REPort", "26.26", "-", "26"),
        ("S_deembed_remote", "DEEMbedding", "26.27", "-", "27"),
        ("S_zvc_remote", "ZVC", "26.28", "-", "28"),
        ("S_sigcfg_remote", "SIGNalconfig", "26.29", "-", "29"),
        ("S_app_jitter", "ADVJitter application", "26.30", "-", "30"),
        ("S_app_lane", "LANE application", "26.31", "-", "31"),
        ("S_app_mtest", "MTESt application", "26.32", "-", "32"),
        ("S_app_eye", "EYE application", "26.33", "-", "33"),
        ("S_app_cdr", "CDR application", "26.34", "-", "34"),
        ("S_app_tdrt", "TDRT application", "26.35", "-", "35"),
        ("S_app_diff", "DIFFerential application", "26.36", "-", "36"),
        ("S_app_iq", "IQ application", "26.37", "-", "37"),
        ("S_trace_remote", "Remote trace and DIAGnostic", "26.38", "-", "38"),
        ("S_deprec_remote", "Deprecated commands", "26.39", "-", "39"),
        ("S_cmd_misc", "Other remote commands", "26.40", "-", "40"),
        ("S_cmd_index", "List of commands index", "index", "-", "41"),
    ]
    sec_lines = [
        f"@SEC: {sid}|ART_rto_um|{heading}|{num}|{parent}|{order}|active|persistent"
        for sid, heading, num, parent, order in secs
    ]
    return (
        """@LAW: LAW-DOC01|*|on_add|locator_not_body|manual_text_stays_in_pdf_file
@LAW: LAW-SCPI01|CMD|on_add|one_cmd_per_row|scpi_tree_in_cmd_field_not_prose
@LAW: LAW-SCPI02|CMD|on_add|stdin_for_special|pipe_question_brackets_via_stdin_not_inline
@LAW: LAW-SCPI03|*|on_turn|handshake_order|cls_idn_err_before_setup_commands
@LAW: LAW-SCPI04|*|on_turn|remote_order|setup_trig_before_acq_before_meas_read

@CFG: CFG01|rto_remote|ART_rto_um|29|scpi_full_dictionary
@ART: ART_rto_um|R&S RTO User Manual|1332_9725_01/RTO_UserManual_en_29.pdf|instrument_manual|active|persistent

"""
        + "\n".join(sec_lines)
        + """

@CLM: CLM_raw_socket_5025|S_net_lan|interface|tcp_raw_socket_port_5025|active|persistent
@CLM: CLM_scpi_ascii|S_scpi_basics|syntax|ascii_over_physical_layer|active|persistent
@CLM: CLM_set_vs_query|S_scpi_basics|syntax|question_suffix_denotes_query|active|persistent
@CLM: CLM_err_drain|S_cmd_syst|procedure|read_syst_err_until_no_error|active|persistent
@CLM: CLM_hello_seq|S_cmd_common|procedure|connect_handshake_five_steps|active|persistent
@CLM: CLM_setup_seq|S_chan_remote|procedure|chan_tbase_trig_before_capture|active|persistent
@CLM: CLM_capture_seq|S_acq_remote|procedure|acq_mode_run_opc|active|persistent
@CLM: CLM_meas_seq|S_meas_remote|procedure|meas_enab_then_result|active|persistent
@CLM: CLM_full_dict|S_cmd_index|fact|full_list_of_commands_rev29|active|persistent

@ENT: ENT_scpi|SCPI|protocol|scpi_tree|persistent
@ENT: ENT_lan|LAN|transport|ethernet_rj45|persistent
@ENT: ENT_raw_socket|raw_socket|transport|tcp_5025|persistent
@ENT: ENT_channel|channel|concept|analog_input|persistent
@ENT: ENT_timebase|timebase|concept|horizontal_scale|persistent
@ENT: ENT_trigger|trigger|concept|acquisition_arm|persistent
@ENT: ENT_waveform|waveform|concept|digitised_trace|persistent
@ENT: ENT_meas_result|meas_result|concept|computed_readout|persistent
@ENT: ENT_status_byte|status_byte|concept|ieee488_stb|persistent
@ENT: ENT_error_queue|error_queue|concept|syst_err_chain|persistent

@TSK: TSK_rto_hello|Connect and print IDN|CLM_hello_seq|in_progress|persistent
@TSK: TSK_rto_capture_ch1|CH1 capture and peak-to-peak|CLM_setup_seq|pending|persistent

"""
    )


def find_cmd_id(scpi_to_id: dict[str, str], *candidates: str) -> str:
    for c in candidates:
        key = normalize_scpi(c).upper()
        if key in scpi_to_id:
            return scpi_to_id[key]
        if key.endswith("?"):
            alt = key[:-1]
            if alt in scpi_to_id:
                return scpi_to_id[alt]
        else:
            alt = key + "?"
            if alt in scpi_to_id:
                return scpi_to_id[alt]
    raise KeyError(f"no CMD for {candidates}")


def build_procedure_edges(scpi_to_id: dict[str, str]) -> str:
    cls = find_cmd_id(scpi_to_id, "*CLS")
    idn = find_cmd_id(scpi_to_id, "*IDN?")
    rst = find_cmd_id(scpi_to_id, "*RST")
    opc = find_cmd_id(scpi_to_id, "*OPC?", "*OPC")
    err = find_cmd_id(scpi_to_id, "*ESR?", ":SYSTem:ERRor?")
    chan = find_cmd_id(scpi_to_id, ":CHANnel<ch>:SCALe", ":CHANnel1:SCALe")
    tbase = find_cmd_id(scpi_to_id, ":TIMebase:SCALe")
    trig_sour = find_cmd_id(scpi_to_id, ":TRIGger<t>:SOURce[:SELect]", ":TRIGger:SOURce")
    trig_mode = find_cmd_id(scpi_to_id, ":TRIGger<t>:MODE", ":TRIGger:MODE")
    trig_lev = find_cmd_id(
        scpi_to_id,
        ":TRIGger<t>:LEVel<n>[:VALue]",
        ":TRIGger<t>:LEVel<n>",
        ":TRIGger:LEVel1",
    )
    run = find_cmd_id(scpi_to_id, ":RUNSingle", ":RUN", ":ACQuire:MODE")
    meas_enab = find_cmd_id(
        scpi_to_id,
        ":MEASurement<mg>[:ENABle]",
        ":MEASurement1:ENABle",
        ":MEASurement<m>:ENABle",
    )
    meas_res = find_cmd_id(
        scpi_to_id,
        ":MEASurement<mg>:RESult[:ACTual]?",
        ":MEASurement<mg>:RESult?",
        ":MEASurement1:RESult?",
    )
    edges = [
        ("E_hello_1", "CLM_hello_seq", "precedes", cls, "step1"),
        ("E_hello_2", cls, "precedes", idn, "step2"),
        ("E_hello_3", idn, "precedes", rst, "step3"),
        ("E_hello_4", rst, "precedes", opc, "step4"),
        ("E_hello_5", opc, "precedes", err, "step5"),
        ("E_setup_1", "CLM_setup_seq", "precedes", chan, "step1"),
        ("E_setup_2", chan, "precedes", tbase, "step2"),
        ("E_setup_3", tbase, "precedes", trig_sour, "step3"),
        ("E_setup_4", trig_sour, "precedes", trig_mode, "step4"),
        ("E_setup_5", trig_mode, "precedes", trig_lev, "step5"),
        ("E_setup_req", "CLM_setup_seq", "requires", "CLM_hello_seq", "after_connect"),
        ("E_cap_1", "CLM_capture_seq", "precedes", run, "step1"),
        ("E_cap_2", run, "precedes", opc, "step2"),
        ("E_cap_req", "CLM_capture_seq", "requires", "CLM_setup_seq", "after_setup"),
        ("E_meas_1", "CLM_meas_seq", "precedes", meas_enab, "step1"),
        ("E_meas_2", meas_enab, "precedes", meas_res, "step2"),
        ("E_meas_req", "CLM_meas_seq", "requires", "CLM_capture_seq", "after_opc"),
        ("E_tsk_hello", "TSK_rto_hello", "owns", "CLM_hello_seq", "focus"),
        ("E_tsk_cap", "TSK_rto_capture_ch1", "owns", "CLM_setup_seq", "focus"),
        ("E_dict", "CLM_full_dict", "mentions", "ENT_scpi", "full_dict"),
        ("E_net_clm", "S_net_lan", "contains", "CLM_raw_socket_5025", "claim"),
        ("E_index", "S_cmd_index", "contains", "CLM_full_dict", "index"),
    ]
    return "\n".join(
        f"@EDG: {eid}|{src}|{rel}|{dst}|{note}|persistent" for eid, src, rel, dst, note in edges
    )


def main() -> int:
    if not PDF.is_file():
        print(f"missing PDF: {PDF}", file=sys.stderr)
        return 1

    text = pdftotext_list_section()
    commands = extract_list_of_commands(text)
    if not commands:
        print("no commands extracted", file=sys.stderr)
        return 1

    OUT_CMD.parent.mkdir(parents=True, exist_ok=True)
    OUT_CMD.write_text(
        "\n".join(f"{scpi}\t{page}" for scpi, page in commands) + "\n",
        encoding="utf-8",
    )

    used_ids: set[str] = set()
    cmd_lines: list[str] = []
    scpi_to_id: dict[str, str] = {}
    sec_cmd_count: dict[str, int] = {}

    for scpi, page in commands:
        sec = subsystem_from_scpi(scpi)
        slug = slug_from_scpi(scpi, used_ids)
        cmd_id = f"CMD_{slug}"
        scpi_to_id[scpi.upper()] = cmd_id
        role = role_from_scpi(scpi)
        params = params_code_from_scpi(scpi)
        scpi_field = scpi.replace("|", "\\|")
        cmd_lines.append(
            f"@CMD: {cmd_id}|{sec}|{scpi_field}|{role}|{params}|active|persistent"
        )
        sec_cmd_count[sec] = sec_cmd_count.get(sec, 0) + 1

    try:
        proc_edges = build_procedure_edges(scpi_to_id)
    except KeyError as exc:
        print(f"warning: procedure edge resolution: {exc}", file=sys.stderr)
        proc_edges = ""

    contain_edges: list[str] = []
    for scpi, page in commands:
        sec = subsystem_from_scpi(scpi)
        cmd_id = scpi_to_id[scpi.upper()]
        contain_edges.append(
            f"@EDG: E_{cmd_id}_in|{sec}|contains|{cmd_id}|cmd|persistent"
        )

    body = (
        build_wire_prefix()
        + "\n".join(cmd_lines)
        + "\n\n"
        + proc_edges
        + "\n\n"
        + "\n".join(contain_edges)
        + "\n"
    )

    OUT_WIRE.write_text(body, encoding="utf-8")
    print(f"extracted {len(commands)} unique commands")
    print(f"wrote {OUT_WIRE} ({OUT_WIRE.stat().st_size // 1024} KB)")
    for sec, n in sorted(sec_cmd_count.items(), key=lambda x: -x[1])[:15]:
        print(f"  {sec}: {n}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
