import re


INPUT_FILE = "pdb_tables.h"
OUTPUT_FILE = "pdb_tables.s"


# name, expected number of elements, assembly directive, values per line
TABLES = [
    ("pdb_orientation", 729, "byte", 16),
    ("pdb_permutation", 5040, "byte", 16),
    ("ori_trans", 729 * 3, "half", 12),
    ("perm_trans", 5040 * 3, "half", 12),
]


def extract_array(text, name):
    """
    從 C header 中抓出指定 array 的 initializer。

    可以處理：

        uint8_t pdb_orientation[729] = {
            ...
        };

        const uint8_t pdb_orientation[729] = {
            ...
        };

        uint16_t ori_trans[729][3] = {
            ...
        };

        const uint16_t ori_trans[729][3] = {
            ...
        };
    """

    # 找到：
    #
    # ori_trans ... = {
    #
    # 不管中間有幾個 []、const、static 等
    pattern = rf"""
        \b{re.escape(name)}\b
        \s*
        (?:\[[^\]]*\]\s*)+
        =
        \s*
        \{{
    """

    match = re.search(
        pattern,
        text,
        re.DOTALL | re.VERBOSE
    )

    if not match:
        raise ValueError(f"找不到 table 宣告: {name}")

    start = match.end()

    # --------------------------------------------------
    # 從第一個 { 開始找對應的 }
    # 因為 ori_trans / perm_trans 是二維陣列，
    # 中間會有很多 { ... }，所以不能直接用 .*?
    # --------------------------------------------------

    brace_level = 1
    i = start

    while i < len(text) and brace_level > 0:

        if text[i] == "{":
            brace_level += 1

        elif text[i] == "}":
            brace_level -= 1

        i += 1

    if brace_level != 0:
        raise ValueError(f"{name} 的大括號沒有正確結束")

    body = text[start:i - 1]

    # --------------------------------------------------
    # 抓所有十進位整數
    # --------------------------------------------------

    values = [
        int(x)
        for x in re.findall(r"\b\d+\b", body)
    ]

    return values


def write_assembly_table(
    f,
    name,
    values,
    directive,
    per_line
):
    f.write(f"{name}:\n")

    for i in range(0, len(values), per_line):

        chunk = values[i:i + per_line]

        f.write(
            f"    .{directive} "
            + ", ".join(str(x) for x in chunk)
            + "\n"
        )

    f.write("\n")


def main():

    # ==================================================
    # 讀取 pdb_tables.h
    # ==================================================

    with open(
        INPUT_FILE,
        "r",
        encoding="utf-8"
    ) as f:
        text = f.read()


    tables = {}


    # ==================================================
    # 讀取四個 table
    # ==================================================

    for (
        name,
        expected_count,
        directive,
        per_line
    ) in TABLES:

        print(f"Reading {name} ...")

        values = extract_array(
            text,
            name
        )

        actual_count = len(values)

        print(
            f"    found: {actual_count}"
        )

        print(
            f"    expected: {expected_count}"
        )

        # ----------------------------------------------
        # 檢查數量
        # ----------------------------------------------

        if actual_count != expected_count:

            raise ValueError(
                f"\n"
                f"{name} 數量錯誤！\n"
                f"預期: {expected_count}\n"
                f"實際: {actual_count}\n"
            )


        # ----------------------------------------------
        # 檢查數值範圍
        # ----------------------------------------------

        if directive == "byte":

            for i, value in enumerate(values):

                if not 0 <= value <= 255:

                    raise ValueError(
                        f"{name}[{i}] = {value} "
                        f"超出 uint8_t 範圍"
                    )


        elif directive == "half":

            for i, value in enumerate(values):

                if not 0 <= value <= 65535:

                    raise ValueError(
                        f"{name}[{i}] = {value} "
                        f"超出 uint16_t 範圍"
                    )


        tables[name] = (
            values,
            directive,
            per_line
        )


    # ==================================================
    # 寫入 assembly
    # ==================================================

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        f.write(".section .rodata\n\n")


        # ==================================================
        # pdb_orientation
        # ==================================================

        f.write(".align 2\n")

        write_assembly_table(
            f,
            "pdb_orientation",
            *tables["pdb_orientation"]
        )


        # ==================================================
        # pdb_permutation
        # ==================================================

        f.write(".align 2\n")

        write_assembly_table(
            f,
            "pdb_permutation",
            *tables["pdb_permutation"]
        )


        # ==================================================
        # ori_trans
        # ==================================================

        f.write(".align 1\n")

        write_assembly_table(
            f,
            "ori_trans",
            *tables["ori_trans"]
        )


        # ==================================================
        # perm_trans
        # ==================================================

        f.write(".align 1\n")

        write_assembly_table(
            f,
            "perm_trans",
            *tables["perm_trans"]
        )


    print()
    print("====================================")
    print("轉換完成")
    print(f"輸出檔案: {OUTPUT_FILE}")
    print("====================================")


if __name__ == "__main__":
    main()
