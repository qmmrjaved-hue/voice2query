import sys
sys.path.insert(0, "c:/voice2query")
import pipeline

result = pipeline.run(
    db_path="c:/voice2query/school.db",
    text="List all students in class TPR1",
)

print()
if result["error"]:
    print("ERROR [" + result["stage"] + "]: " + result["error"])
else:
    print("=== SQL ===")
    print(result["sql"])
    print()
    print("=== Results ===")
    print(result["results"].to_string(index=False))
