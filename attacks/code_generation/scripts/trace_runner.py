import json
import sys
import time
import os
import io
import ast
from attacks.code_generation.utils import obtain_private_test_cases, parse_output, clean_llm_code

llm_prog = clean_llm_code(sys.argv[1])
public_test_cases_json = sys.argv[2]
temp_b64_path = sys.argv[3]
atk_type = sys.argv[4]
func_entrypoint = sys.argv[5] if len(sys.argv) > 5 else None

evaluation = {}

# obtaining public and private test cases
public_test_cases = json.loads(public_test_cases_json)
private_test_cases = []
parent_b64_path = os.path.dirname(temp_b64_path)
try:
    with open(temp_b64_path, 'r') as f:
        private_b64 = f.read()
    private_test_cases = obtain_private_test_cases(private_b64)
except Exception as e:
    pass

test_cases = public_test_cases + private_test_cases

results = {}
executed_lines = {}

def trace_fn(frame, event, arg):
    if event == 'call':
        return trace_fn  # keep tracing this frame
    if event == 'line' and frame.f_code.co_filename == '<string>':
        lineno = frame.f_lineno
        executed_lines[lineno] = executed_lines.get(lineno, 0) + 1
    return trace_fn

for idx, test_case in enumerate(test_cases):
    trace_data = {}
    executed_lines.clear()
    program_output =None
    test_case_key = f"test_case_{idx}"
    
    # Start timer
    start_time = time.time() 
    test_input = test_case['input']

    # print(f"DEBUG test_input: {repr(test_input)}", file=sys.stderr)

    test_output = test_case['output'].strip() if isinstance(test_case['output'], str) else test_case['output']
    test_type = test_case['testtype']

    if len(func_entrypoint) > 0 and test_type == 'functional':
        namespace = {
            '__name__': '__main__',
            '__builtins__': __builtins__,
        }
        compiled = compile(llm_prog, '<string>', 'exec')
        sys.settrace(trace_fn)
        try:
            exec(compiled, namespace, namespace)
            lines = test_input.strip().splitlines()
            _args = tuple(ast.literal_eval(line) for line in lines)
            program_output = getattr(namespace['Solution'](), func_entrypoint)(*_args)
        finally:
            sys.settrace(None)
        trace_data = executed_lines.copy()
    else:
        old_stdin = sys.stdin
        old_stdout = sys.stdout

        fake_stdin = io.StringIO(test_input)
        fake_stdin.buffer = io.BytesIO(test_input.encode())
        sys.stdin = fake_stdin
        sys.stdout = io.StringIO()

        try:
            namespace = {
                '__name__': '__main__',
                '__builtins__': __builtins__,
            }
            compiled = compile(llm_prog, '<string>', 'exec')
            sys.settrace(trace_fn)
            exec(compiled, namespace, namespace)
            program_output = sys.stdout.getvalue().strip()
        except Exception as e:
            raise RuntimeError(f"Code execution failed:\n{e}")
        finally:
            sys.settrace(None)
            sys.stdin = old_stdin
            sys.stdout = old_stdout

        trace_data = executed_lines.copy()

    # End timer
    elapsed_time = time.time() - start_time
    
    # Evaluate Model Correctness
    if test_type == 'functional':
        passed = program_output == parse_output(test_output)
    else:
        passed = program_output == test_output

    results[test_case_key] = {
        'passed' : passed,
        'executed_lines': trace_data,
        'time_seconds': elapsed_time
    }
    

print(json.dumps(results))