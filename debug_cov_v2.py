from coverage import CoverageData


def inspect_coverage():
    try:
        data = CoverageData()
        data.read()
        print(f"Measured files: {len(data.measured_files())}")
        if not data.measured_files():
            print("No files measured.")
            return

        for filename in list(data.measured_files())[:5]:
            contexts = data.contexts_by_lineno(filename)
            print(f"File: {filename}")
            print(f"Contexts keys: {list(contexts.keys())[:5]}")
            # Check for non-empty contexts
            all_contexts = set()
            for lines in contexts.values():
                all_contexts.update(lines)

            print(f"Unique contexts: {list(all_contexts)[:5]}")

    except Exception as e:
        print(f"Error reading coverage: {e}")


if __name__ == "__main__":
    inspect_coverage()
