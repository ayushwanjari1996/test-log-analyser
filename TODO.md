# TODO - Future Enhancements

## 1. Infrastructure Entity Support

**Priority:** Medium  
**Status:** Planned  
**Created:** November 29, 2025

### Current Situation

Log format has two types of data:
1. **JSON Log Content** (column: `_source.log`) - Contains actual log entities (CM MAC, CPE IP, RPD names, etc.)
2. **CSV Metadata** (columns: `_source.pod_ip`, `_source.node_name`, `_source.cluster_name`, etc.) - Contains infrastructure info

**Current Implementation:**
- Entity extraction ONLY searches `_source.log` column
- CSV metadata columns are ignored to prevent noise (e.g., pod IPs being treated as entity IPs)

### Future Enhancement Needed

Infrastructure metadata can be valuable for:
- **Troubleshooting pod/container issues**: "Which pod is CM x running on?"
- **Cluster analysis**: "Show all logs from node Y"
- **Infrastructure correlation**: "Did pod restart cause CM offline?"
- **Multi-tenancy**: "Show all logs from namespace Z"

### Implementation Plan

#### Phase 1: CSV Header Mapping
- Read CSV header (line 1) to map column positions to names
- Create mapping between CSV column indices and semantic names
- Store mapping in config or dynamically detect

**Example:**
```python
csv_columns = {
    6: "pod_ip",           # _source.pod_ip
    7: "namespace_name",   # _source.namespace_name
    8: "k8s_cluster",      # _source.k8s_cluster
    9: "application_name", # _source.application_name
    10: "host",            # _source.host
    # ... etc
}
```

#### Phase 2: Infrastructure Entity Types

Add new entity types in `config/entity_mappings.yaml`:

```yaml
# Infrastructure entities
infrastructure_entities:
  pod_name:
    column: "_source.pod_name"
    patterns:
      - "mawepp\\d+-w\\d+"
      - "[a-z]+pp[a-z0-9-]+"
  
  node_name:
    column: "_source.node_name"
    patterns:
      - "mawe[a-z]+\\d+"
  
  cluster_name:
    column: "_source.cluster_name"
    patterns:
      - "mawe[a-z]+\\d+"
  
  namespace:
    column: "_source.namespace"
    patterns:
      - "[a-z]+"
  
  container_name:
    column: "_source.container_name"
    patterns:
      - "[a-z_-]+"
```

#### Phase 3: Selective Entity Extraction

Create entity extraction profiles:

```yaml
extraction_profiles:
  log_entities_only:
    columns: ["_source.log"]
    entity_types: ["cm", "cpe_mac", "cpe_ip", "rpdname", "md_id", "sf_id"]
  
  infrastructure_only:
    columns: ["_source.pod_name", "_source.node_name", "_source.cluster_name"]
    entity_types: ["pod_name", "node_name", "cluster_name"]
  
  full_extraction:
    columns: "all"
    entity_types: "all"
```

#### Phase 4: Query Support

Support infrastructure queries:

```
# Infrastructure queries
which pod is cm 10:e1:77:08:63:8a running on?
show all logs from node maweds105
analyse pod mawepp105-w03
why did container mulpi restart?

# Combined queries
find cm on pod mawepp105-w03
show all cms in cluster mawecc101
```

#### Phase 5: Correlation Analysis

Enable infrastructure-entity correlation:

```python
# Example: Correlate CM offline with pod events
if cm_offline:
    check_pod_logs(cm_pod_name)
    check_node_health(cm_node_name)
    check_container_restarts(cm_container)
```

### Technical Considerations

**Challenges:**
1. **Performance**: Extracting from all columns increases processing time
2. **Noise**: Infrastructure values are repetitive (same pod_ip in many logs)
3. **Context**: Need to know when to use infra entities vs log entities
4. **Priority**: Log entities should take precedence in searches

**Solutions:**
1. **Lazy Loading**: Only extract infrastructure entities when explicitly requested
2. **Caching**: Cache infrastructure entity values (they change rarely)
3. **Query Intent**: LLM determines if query needs infrastructure context
4. **Separate Namespaces**: Keep log entities and infra entities in different namespaces

### Configuration Example

```yaml
# config/entity_extraction.yaml
entity_extraction:
  default_profile: "log_entities_only"  # Default: ignore CSV metadata
  
  profiles:
    log_entities_only:
      enabled: true
      columns: ["_source.log"]
      
    infrastructure:
      enabled: false  # Enable when needed
      columns: 
        - "_source.pod_name"
        - "_source.node_name"
        - "_source.cluster_name"
        - "_source.namespace"
        - "_source.host"
      
  infrastructure_entity_priority: 3  # Lower than log entities (priority 5-10)
```

### Related Files to Modify

- `src/core/entity_manager.py` - Add infrastructure entity extraction
- `src/core/log_processor.py` - Add CSV header parsing
- `config/entity_mappings.yaml` - Add infrastructure entity patterns
- `config/entity_extraction.yaml` - New config for extraction profiles
- `src/core/llm_query_parser.py` - Teach LLM about infrastructure entities

### Testing

Test queries:
```
# Should work after implementation
which pod is running cm 10:e1:77:08:63:8a?
show logs from node maweds105
analyse container mulpi for errors
find all cms in namespace vcmts_mulpi
did pod restart cause cm offline?
```

---

## 2. Other Future Enhancements

### 2.1 Performance Optimization
- Cache LLM responses for similar queries
- Parallel entity extraction
- Indexed log search

### 2.2 Advanced Analysis
- Time-series anomaly detection
- Pattern prediction
- Proactive alerting

### 2.3 Multi-Log Source Support
- Support multiple CSV files
- Support JSON logs directly
- Support syslog format

---

**Last Updated:** November 29, 2025  
**Status:** Active planning document

