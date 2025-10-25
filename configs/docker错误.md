phoenix_db  | PostgreSQL Database directory appears to contain a database; Skipping initialization                                                                                                            
phoenix_db  | 
phoenix_db  | 2025-10-25 06:41:03.559 UTC [1] LOG:  starting PostgreSQL 15.14 on x86_64-pc-linux-musl, compiled by gcc (Alpine 14.2.0) 14.2.0, 64-bit                                                         
phoenix_db  | 2025-10-25 06:41:03.559 UTC [1] LOG:  listening on IPv4 address "0.0.0.0", port 5432                                                                                                            
phoenix_db  | 2025-10-25 06:41:03.559 UTC [1] LOG:  listening on IPv6 address "::", port 5432                                                                                                                 
phoenix_db  | 2025-10-25 06:41:03.569 UTC [1] LOG:  listening on Unix socket "/var/run/postgresql/.s.PGSQL.5432"                                                                                              
phoenix_db  | 2025-10-25 06:41:03.596 UTC [29] LOG:  database system was shut down at 2025-10-25 05:37:20 UTC
phoenix_db  | 2025-10-25 06:41:03.602 UTC [29] LOG:  invalid magic number 0000 in log segment 000000010000000000000001, offset 14696448                                                                       
phoenix_db  | 2025-10-25 06:41:03.602 UTC [29] LOG:  invalid primary checkpoint record                                                                                                                        
phoenix_db  | 2025-10-25 06:41:03.602 UTC [29] PANIC:  could not locate a valid checkpoint record                                                                                                             
phoenix_db  | 2025-10-25 06:41:04.155 UTC [1] LOG:  startup process (PID 29) was terminated by signal 6: Aborted                                                                                              
phoenix_db  | 2025-10-25 06:41:04.155 UTC [1] LOG:  aborting startup due to startup process failure
phoenix_db  | 2025-10-25 06:41:04.159 UTC [1] LOG:  database system is shut down                                                                                                                              
Gracefully Stopping... press Ctrl+C again to force                                                                                                                                                            
dependency failed to start: container phoenix_db is unhealthy