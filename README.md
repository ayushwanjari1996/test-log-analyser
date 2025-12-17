NOTE: still under development. **Some features might not work.**

**Check arch.md for understand code architecture**

AI log QnA + analyser using locally deployed llm.

Step 1) install ollama cli
Step 2) pull qwen3 thinking model and build it using modelFile defined in code.
Step 3) Get a test file (something like test.csv) and start chat by doing chat.py.


For personal/new logs, you might need to update entity_mappings.yaml


Sample run below:

```text
PS C:\Users\AYUSH\work\ai-stuff\test-AI-log-engine> python chat.py

Initializing orchestrator...
[12/17/25 19:12:53] INFO     Initializing IterativeReactOrchestrator
                    INFO       Log file: test.csv
                    INFO       Model: qwen3-react
                    INFO       Max iterations: 10
                    INFO     Initialized OllamaClient (base_url=http://localhost:11434, model=qwen3-react)
                    INFO     LLM client initialized: qwen3-react
                    INFO     StreamSearcher initialized for test.csv
                    INFO     StreamSearcher initialized for test.csv
                    INFO     StreamSearcher initialized for test.csv
                    INFO     Initialized OllamaClient (base_url=http://localhost:11434, model=qwen3-loganalyzer)
                    INFO     Registered 15 tools
                    INFO     IterativeReactOrchestrator ready with SmartSummarizer
✓ Orchestrator initialized

╭──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ ┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓ │
│ ┃                                      🤖 AI Log Analyzer - Interactive Chat                                       ┃ │
│ ┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛ │
│                                                                                                                      │
│ Orchestrator: Iterative ReAct Log File: test.csv Max Iterations: 10                                                  │
│                                                                                                                      │
│                                                                                                                      │
│                                                      Commands:                                                       │
│                                                                                                                      │
│  • Type your question naturally (e.g., "count all error logs")                                                       │
│  • /help - Show this help                                                                                            │
│  • /history - View chat history                                                                                      │
│  • /stats - Show session statistics                                                                                  │
│  • /clear - Clear screen                                                                                             │
│  • /exit or /quit - Exit chat                                                                                        │
│                                                                                                                      │
│                                                                                                                      │
│                                                   Example Queries:                                                   │
│                                                                                                                      │
│  • "count all logs"                                                                                                  │
│  • "show error logs"                                                                                                 │
│  • "count unique CM MACs"                                                                                            │
│  • "find logs for MAWED07T01"                                                                                        │
│  • "list all RPDs in warning logs"                                                                                   │
│                                                                                                                      │
│ Ready to analyze! 🚀                                                                                                 │
╰──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯

You: count unique CM MACs
Thinking...

======================================================================
PROCESSING QUERY: count unique CM MACs
======================================================================

Starting iterative analysis (max 10 iterations)...

======================================================================
ITERATION 1/10
Query: count unique CM MACs
======================================================================
[12/17/25 19:13:44] INFO     Generation successful: 515 chars, took 21.72s

======================================================================
[FULL PROMPT TO LLM]
======================================================================
You are analyzing logs to answer a query. Decide the NEXT action.

QUERY: count unique CM MACs
ITERATION: 1/10

PREVIOUS ACTIONS: None (first iteration)

CURRENT STATE:
  No logs loaded yet
DECISION POINT:
- Have enough data? → finalize_answer
- Need more data? → call next tool

FORMAT (KEEP BRIEF):
<think>1-2 sentence max</think>
{
  "reasoning": "one sentence",
  "action": "tool_name",
  "params": {dict}
}

CRITICAL:
- Return JSON ONLY


======================================================================
[FULL LLM RESPONSE]
======================================================================
<think>Okay, the user wants to count unique CM MACs. First, I need to get the logs that contain CM MAC addresses. Since there are no logs loaded yet, the first step is to search for logs with the pattern "CmMacAddress". This will retrieve all relevant logs. Once I have those logs, I can proceed to count the unique values. So the next action is to use grep_logs with the pattern "CmMacAddress".
</think>

{"reasoning": "Need to find logs with CM MACs", "action": "grep_logs", "params": {"pattern": "CmMacAddress"}}
======================================================================

[Parsed Decision]
  Action: grep_logs
  Params: {'pattern': 'CmMacAddress'}
                    INFO     Streaming search for: 'CmMacAddress' (case_sensitive=False, regex=False)
                    INFO     Found 101 matches out of 200 lines scanned

[Tool Result]
  ✓ [RAW DATA] Found 101 log entries matching 'CmMacAddress' - may contain duplicates

======================================================================
ITERATION 2/10
Query: count unique CM MACs
======================================================================
[12/17/25 19:13:48] INFO     Generation successful: 133 chars, took 2.12s

======================================================================
[FULL PROMPT TO LLM]
======================================================================
You are analyzing logs to answer a query. Decide the NEXT action.

QUERY: count unique CM MACs
ITERATION: 2/10

PREVIOUS ACTIONS:
  Step 1: grep_logs({'pattern': 'CmMacAddress'})
    → [RAW DATA] Found 101 log entries matching 'CmMacAddress' - may contain duplicates

CURRENT STATE:
  Logs loaded: 101 entries (DataFrame)

  💡 HINT: Query needs unique values. Logs loaded but no fields extracted yet. Use parse_json_field to extract the field you need.
DECISION POINT:
- Have enough data? → finalize_answer
- Need more data? → call next tool

FORMAT (KEEP BRIEF):
<think>1-2 sentence max</think>
{
  "reasoning": "one sentence",
  "action": "tool_name",
  "params": {dict}
}

CRITICAL:
- Return JSON ONLY


======================================================================
[FULL LLM RESPONSE]
======================================================================
<think>
</think>

{"reasoning": "Extract CmMacAddress field", "action": "parse_json_field", "params": {"field_name": "CmMacAddress"}}
======================================================================

[Parsed Decision]
  Action: parse_json_field
  Params: {'field_name': 'CmMacAddress'}

[Tool Result]
  ✓ [RAW DATA] Extracted 47 raw values for 'CmMacAddress' - may contain duplicates

======================================================================
ITERATION 3/10
Query: count unique CM MACs
======================================================================
[12/17/25 19:13:52] INFO     Generation successful: 133 chars, took 2.27s

======================================================================
[FULL PROMPT TO LLM]
======================================================================
You are analyzing logs to answer a query. Decide the NEXT action.

QUERY: count unique CM MACs
ITERATION: 3/10

PREVIOUS ACTIONS:
  Step 1: grep_logs({'pattern': 'CmMacAddress'})
    → [RAW DATA] Found 101 log entries matching 'CmMacAddress' - may contain duplicates
  Step 2: parse_json_field({'field_name': 'CmMacAddress', 'logs':                           _index  ... _source.container_name_key
0    logstash-2025-11-05-[12-16]  ...                      mulpi
1    logstash-2025-11-05-[12-16]  ...                      mulpi
2    logstash-2025-11-05-[12-16]  ...                      mulpi
3    logstash-2025-11-05-[12-16]  ...                      mulpi
4    logstash-2025-11-05-[12-16]  ...                      mulpi
..                           ...  ...                        ...
96   logstash-2025-11-05-[12-16]  ...                      mulpi
97   logstash-2025-11-05-[12-16]  ...                      mulpi
98   logstash-2025-11-05-[12-16]  ...                      mulpi
99   logstash-2025-11-05-[12-16]  ...                      mulpi
100  logstash-2025-11-05-[12-16]  ...                      mulpi

[101 rows x 27 columns]})
    → [RAW DATA] Extracted 47 raw values for 'CmMacAddress' - may contain duplicates

CURRENT STATE:
  Logs loaded: 101 entries (DataFrame)

  Extracted fields:
    - CmMacAddress: 47 raw (may have duplicates) values (in last_result)

  Last result: 47 values (sample: ['b3:f1:7b:9e:92:bc', '3f:b2:1e:4b:fb:3c', 'f7:f9:28:3c:22:45'])

  💡 HINT: Query needs unique count. Raw values extracted but not deduplicated. Next: count_values() - values will be auto-used from last_result
DECISION POINT:
- Have enough data? → finalize_answer
- Need more data? → call next tool

FORMAT (KEEP BRIEF):
<think>1-2 sentence max</think>
{
  "reasoning": "one sentence",
  "action": "tool_name",
  "params": {dict}
}

CRITICAL:
- Return JSON ONLY


======================================================================
[FULL LLM RESPONSE]
======================================================================
<think>
</think>

{"reasoning": "Count unique CM MACs from extracted values", "action": "count_values", "params": {"values": [".*"]}}
======================================================================

[Parsed Decision]
  Action: count_values
  Params: {'values': ['.*']}
                    INFO       🔧 Detected sample values (1 items), replacing with full dataset (47 items)

[Tool Result]
  ✓ [FINAL COUNT] 47 unique values (from 47 total entries)

======================================================================
ITERATION 4/10
Query: count unique CM MACs
======================================================================
[12/17/25 19:13:58] INFO     Generation successful: 156 chars, took 3.69s

======================================================================
[FULL PROMPT TO LLM]
======================================================================
You are analyzing logs to answer a query. Decide the NEXT action.

QUERY: count unique CM MACs
ITERATION: 4/10

PREVIOUS ACTIONS:
  Step 1: grep_logs({'pattern': 'CmMacAddress'})
    → [RAW DATA] Found 101 log entries matching 'CmMacAddress' - may contain duplicates
  Step 2: parse_json_field({'field_name': 'CmMacAddress', 'logs':                           _index  ... _source.container_name_key
0    logstash-2025-11-05-[12-16]  ...                      mulpi
1    logstash-2025-11-05-[12-16]  ...                      mulpi
2    logstash-2025-11-05-[12-16]  ...                      mulpi
3    logstash-2025-11-05-[12-16]  ...                      mulpi
4    logstash-2025-11-05-[12-16]  ...                      mulpi
..                           ...  ...                        ...
96   logstash-2025-11-05-[12-16]  ...                      mulpi
97   logstash-2025-11-05-[12-16]  ...                      mulpi
98   logstash-2025-11-05-[12-16]  ...                      mulpi
99   logstash-2025-11-05-[12-16]  ...                      mulpi
100  logstash-2025-11-05-[12-16]  ...                      mulpi

[101 rows x 27 columns]})
    → [RAW DATA] Extracted 47 raw values for 'CmMacAddress' - may contain duplicates
  Step 3: count_values({'values': ['b3:f1:7b:9e:92:bc', '3f:b2:1e:4b:fb:3c', 'f7:f9:28:3c:22:45', '34:30:ed:0b:c5:31', '4b:df:5d:f3:71:89', '54:e9:c9:61:fe:84', '81:03:a5:a8:4a:46', '2d:a7:26:aa:fb:65', '59:1f:3c:f2:a6:8b', '6b:d1:14:26:17:68', '8d:b9:1a:44:3b:d9', '1d:7e:bd:cb:fa:6b', 'a3:aa:09:9d:17:28', '94:af:68:3b:69:40', '22:3e:6c:ac:af:97', 'ae:87:f4:94:8b:cc', '8b:4a:06:38:09:8f', 'd3:78:6d:83:14:2d', '21:21:c4:2e:3a:f1', 'c1:c3:b8:c5:1d:2b', '4a:c4:db:9a:2a:2e', '8d:44:23:94:88:19', '6c:8e:b0:01:02:1e', '9c:91:5a:43:dc:b3', 'b8:92:68:03:90:63', '7c:fd:8c:90:6e:26', '5a:4a:21:3c:de:5d', '66:42:bf:cf:10:ff', 'a7:f9:a1:c2:88:70', '21:45:7b:4f:b7:5d', '9d:fc:04:d0:22:c4', 'eb:84:2e:de:49:5b', '5c:b9:8c:88:d2:13', 'b1:8a:9e:02:15:e3', 'e3:49:e3:a0:c3:45', 'de:25:f1:17:ae:ca', 'bf:d3:79:d9:0b:b6', '3f:d4:f1:5c:15:52', '15:de:c0:05:c9:74', 'be:ef:26:3b:66:05', '47:5c:57:0b:f4:55', '08:8d:d3:14:b9:9e', '4d:8c:d8:58:6c:75', 'd0:99:28:47:b1:17', '5f:fc:3f:6c:2e:ef', '46:f6:e1:d3:2e:b5', 'a5:1b:61:fe:ed:e7'], 'logs':                           _index  ... _source.container_name_key
0    logstash-2025-11-05-[12-16]  ...                      mulpi
1    logstash-2025-11-05-[12-16]  ...                      mulpi
2    logstash-2025-11-05-[12-16]  ...                      mulpi
3    logstash-2025-11-05-[12-16]  ...                      mulpi
4    logstash-2025-11-05-[12-16]  ...                      mulpi
..                           ...  ...                        ...
96   logstash-2025-11-05-[12-16]  ...                      mulpi
97   logstash-2025-11-05-[12-16]  ...                      mulpi
98   logstash-2025-11-05-[12-16]  ...                      mulpi
99   logstash-2025-11-05-[12-16]  ...                      mulpi
100  logstash-2025-11-05-[12-16]  ...                      mulpi

[101 rows x 27 columns]})
    → [FINAL COUNT] 47 unique values (from 47 total entries)

CURRENT STATE:
  Logs loaded: 101 entries (DataFrame)

  Extracted fields:
    - CmMacAddress: 47 UNIQUE values (in last_result)
DECISION POINT:
- Have enough data? → finalize_answer
- Need more data? → call next tool

FORMAT (KEEP BRIEF):
<think>1-2 sentence max</think>
{
  "reasoning": "one sentence",
  "action": "tool_name",
  "params": {dict}
}

CRITICAL:
- Return JSON ONLY


======================================================================
[FULL LLM RESPONSE]
======================================================================
<think>
</think>

{
  "reasoning": "Unique CM MACs counted",
  "action": "finalize_answer",
  "params": {"answer": "Found 47 unique CM MACs in the logs."}
}
======================================================================

[Parsed Decision]
  Action: finalize_answer
  Params: {'answer': 'Found 47 unique CM MACs in the logs.'}

✓ FINAL ANSWER: Found 47 unique CM MACs in the logs.
======================================================================

======================================================================
✓ SUCCESS
Answer: Found 47 unique CM MACs in the logs.
Iterations: 4/10
======================================================================

Assistant: Found 47 unique CM MACs in the logs.

You:
```
