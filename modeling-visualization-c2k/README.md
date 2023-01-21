# Graph Data Science for Supply Chains
## Getting Started with Graph Data Modeling, Exploration, and Visualization
![Neo4j version](https://img.shields.io/badge/Neo4j->=4.4.9-brightgreen) 
![GDS version](https://img.shields.io/badge/GDS->=2.2-brightgreen)


This directory contains a notebook and bloom perspective to replicate the analysis in [Graph Data Science for Supply Chains Part I: Getting Started with Neo4j Graph Data Science and Bloom](https://neo4j.com/developer-blog/supply-chain-neo4j-gds-bloom/). That analysis focuses on

1. Graph data modeling and ingest for supply chain
2. Visualising and exploring supply chains processes
3. Identifying and inspecting critical stages and interdependent process using low-code/no-code graph algorithms

There are 2 files:
1. `transform-and-load.ipynb` is a python notebook that downloads the source data (the Cargo 2000 case study dataset) and transforms and loads it into a Neo4j database.
2. `bloom-perspective.json` Contains the [Bloom Perspective](https://neo4j.com/docs/bloom-user-guide/current/bloom-perspectives/bloom-perspectives/) which defines the categorization and styling of entities as well as the search phrases. This can be imported into Bloom to replicate the Bloom visuals in the blog. 
