# ZeroDB MCP Methods - Available via AINative

## Agent Memory Operations
- `zerodb_store_memory` - Store agent memory in ZeroDB for persistent context
- `zerodb_search_memory` - Search agent memory using semantic similarity
- `zerodb_get_context` - Get agent context window for current session

## Vector Database Operations
- `zerodb_upsert_vector` - Store or update a vector embedding with metadata (1536 dimensions)
- `zerodb_batch_upsert_vectors` - Batch upsert multiple vectors for efficiency
- `zerodb_search_vectors` - Search vectors using semantic similarity
- `zerodb_delete_vector` - Delete a specific vector by ID
- `zerodb_get_vector` - Retrieve a specific vector by ID
- `zerodb_list_vectors` - List vectors in a project/namespace with pagination
- `zerodb_vector_stats` - Get vector statistics for a project
- `zerodb_create_vector_index` - Create optimized index for vector search
- `zerodb_optimize_vectors` - Optimize vector storage for better performance
- `zerodb_export_vectors` - Export vectors to various formats (JSON, CSV, Parquet)

## Quantum Operations (Advanced)
- `zerodb_quantum_compress` - Apply quantum-inspired compression to vector
- `zerodb_quantum_decompress` - Decompress quantum-compressed vector
- `zerodb_quantum_hybrid_search` - Hybrid similarity search using quantum enhancement
- `zerodb_quantum_optimize` - Optimize quantum circuits for project vectors
- `zerodb_quantum_feature_map` - Apply quantum feature mapping to vector
- `zerodb_quantum_kernel` - Calculate quantum kernel similarity between vectors

## NoSQL Table Operations
- `zerodb_create_table` - Create a new NoSQL table with schema
- `zerodb_list_tables` - List all tables in the project
- `zerodb_get_table` - Get table details and schema
- `zerodb_delete_table` - Delete a table and all its data
- `zerodb_insert_rows` - Insert rows into a table
- `zerodb_query_rows` - Query rows from a table with filters
- `zerodb_update_rows` - Update rows in a table
- `zerodb_delete_rows` - Delete rows from a table

## File Storage Operations
- `zerodb_upload_file` - Upload file to ZeroDB storage
- `zerodb_download_file` - Download file from ZeroDB storage
- `zerodb_list_files` - List files in project storage
- `zerodb_delete_file` - Delete file from storage
- `zerodb_get_file_metadata` - Get file metadata without downloading content
- `zerodb_generate_presigned_url` - Generate presigned URL for file access

## Event Stream Operations
- `zerodb_create_event` - Create an event in the event stream
- `zerodb_list_events` - List events with filtering
- `zerodb_get_event` - Get event details by ID
- `zerodb_subscribe_events` - Subscribe to event stream (returns subscription ID)
- `zerodb_event_stats` - Get event stream statistics

## Project Management
- `zerodb_create_project` - Create a new ZeroDB project
- `zerodb_get_project` - Get project details
- `zerodb_list_projects` - List all accessible projects
- `zerodb_update_project` - Update project settings
- `zerodb_delete_project` - Delete a project and all its data
- `zerodb_get_project_stats` - Get project usage statistics
- `zerodb_enable_database` - Enable database features for a project

## RLHF (Reinforcement Learning from Human Feedback)
- `zerodb_rlhf_interaction` - Collect user interaction for RLHF training
- `zerodb_rlhf_agent_feedback` - Collect agent-level feedback
- `zerodb_rlhf_workflow` - Collect workflow-level feedback
- `zerodb_rlhf_error` - Collect error report for RLHF improvement
- `zerodb_rlhf_status` - Get RLHF collection status
- `zerodb_rlhf_summary` - Get RLHF data summary and statistics
- `zerodb_rlhf_start` - Start RLHF data collection for session
- `zerodb_rlhf_stop` - Stop RLHF data collection for session
- `zerodb_rlhf_session` - Get RLHF interactions for a session
- `zerodb_rlhf_broadcast` - Broadcast RLHF event to subscribers

## Admin Operations (Admin Only)
- `zerodb_admin_system_stats` - Get system-wide statistics
- `zerodb_admin_list_projects` - List all projects system-wide
- `zerodb_admin_user_usage` - Get user usage statistics
- `zerodb_admin_health` - Get system health status
- `zerodb_admin_optimize` - Run database optimization

## Authentication
- `zerodb_renew_token` - Manually renew authentication token

---

## Key Notes for PublicFounders Implementation

### Vector Dimensions
- All vectors must be exactly **1536 dimensions** (OpenAI embedding standard)

### Free Tier Limits (per project)
- Max projects: 3
- Max vectors: 10,000
- Max tables: 5
- Max events per month: 100,000
- Max storage: 1 GB

### Recommended Usage for PublicFounders
1. **Agent Memory**: Use for virtual advisor context and learning
2. **Vector Storage**: Store founder profiles, goals, asks, posts as embeddings
3. **Semantic Search**: Find relevant founder matches based on intent
4. **NoSQL Tables**: Store relational data (users, companies, introductions)
5. **Event Stream**: Track introduction outcomes and user interactions
6. **RLHF**: Improve agent suggestions based on user feedback
