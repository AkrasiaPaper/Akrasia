import trace
import json
import sys
import time
import io
import os
from attacks.code_generation.utils import check_solution_class

timing_file = os.path.join(os.getcwd(), 'timing_log.txt')
with open(timing_file, 'a') as f:
    f.write(f"Let's go")
    f.flush()  

llm_prog = sys.argv[1]
func_entrypoint = sys.argv[3] if len(sys.argv) > 3 else None
test_cases_json = sys.argv[2]

if func_entrypoint:
    # Execute the LLM program
    exec(llm_prog)

# Parse test cases
test_cases = json.loads(test_cases_json)

results = {}

for idx, test_case in enumerate(test_cases):
    test_case_key = f"test_case_{idx}"
    
    # Start timer
    start_time = time.time()
    with open(timing_file, 'a') as f:
        f.write(f"Starting on test case {idx}\n")
        f.flush()  
    try:
        tracer = trace.Trace(count=True, trace=False)
        test_input = test_case['input']
        
        if func_entrypoint:
            class_name = check_solution_class(llm_prog, func_entrypoint)

            namespace = {'__name__': '__main__'}

            code = f'result = {func_entrypoint}({test_input})'

            tracer.runctx(code, globals(), namespace)

            test_output = namespace.get('result', None)


        else:
            stdin_backup = sys.stdin
            stdout_backup = sys.stdout

            sys.stdin = io.StringIO(str(test_input))
            output_buffer = io.StringIO()
            sys.stdout = output_buffer
            
            try:
                namespace = {'__name__': '__main__'}
                tracer.runctx(llm_prog, globals(), namespace)
                
                test_output = output_buffer.getvalue()
                status = 'success'
                
            except Exception as e:
                test_output = None
                status = 'error'
            
            finally:
                sys.stdin = stdin_backup
                sys.stdout = stdout_backup

        
        # Get the result
        trace_results = tracer.results()
        executed_lines = {}
        for (filename, line_num), count in trace_results.counts.items():
            executed_lines[line_num] = count
        
        # End timer
        elapsed_time = time.time() - start_time
        
        # Store results
        results[test_case_key] = {
            'input': test_input,
            'output': test_output,
            'executed_lines': executed_lines,
            'status': 'success',
            'time_seconds': elapsed_time
        }
        
        with open(timing_file, 'a') as f:
            f.write(f"✓ {test_case_key}: {elapsed_time:.4f}s\n")
            f.flush() 
        
    except Exception as e:
        elapsed_time = time.time() - start_time
        
        results[test_case_key] = {
            'input': test_input,
            'output': None,
            'executed_lines': {},
            'status': 'error',
            'error': str(e),
            'time_seconds': elapsed_time
        }
        
        with open(timing_file, 'a') as f:
            f.write(f"✗ {test_case_key}: {elapsed_time:.4f}s - ERROR: {str(e)}\n")
            f.flush()  

print(json.dumps(results))