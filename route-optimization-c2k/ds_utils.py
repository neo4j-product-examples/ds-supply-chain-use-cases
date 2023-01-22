import pandas as pd
import numpy as np
import graphdatascience
import itertools

from graphdatascience import GraphDataScience


def strfdelta(tdelta, fmt):
    d = {'days': str(tdelta.days).zfill(2)}
    h, rem = divmod(tdelta.seconds, 3600)
    m, s = divmod(rem, 60)
    d['hours'] = str(h).zfill(2)
    d['minutes'] = str(m).zfill(2)
    d['seconds'] = str(s).zfill(2)
    return fmt.format(**d)


def minutes_to_duration(x):
    return pd.to_timedelta(x, unit='m') \
        .apply(lambda x: strfdelta(x, '{days} days, {hours} hrs, {minutes} min'))


def minutes_to_duration_arr(x):
    tds = pd.to_timedelta(x, unit='m')
    return [strfdelta(td, '{days}days-{hours}hrs-{minutes}min') for td in tds]


def minutes_to_duration_arr_col(x):
    return x.apply(minutes_to_duration_arr)


def drop_graph_by_name(gds: GraphDataScience, graph_name: str):
    if gds.graph.exists(graph_name).loc['exists']:
        gds.graph.get(graph_name).drop()


def clear_all_graphs(gds):
    g_names = gds.graph.list().graphName.tolist()
    for g_name in g_names:
        gds.graph.get(g_name).drop()


def historic_path_counts(gds, sid, tid):
    df = gds.run_cypher('''
        //match incoming legIds (incoming leg numbers are > 0)
        MATCH(:EntryPoint {airportId: $sourceAirportId})-[r:RECEPTION]->() WHERE r.legNumber > 0
        WITH r.legId AS incomingLegId, r.shipmentId AS shipmentId

        //filter to only shipmentIds that go to target airport
        MATCH()-[:DELIVERY {shipmentId:shipmentId}]->(:Destination {airportId: $targetAirportId})
        WITH incomingLegId, shipmentId

        //get transfer point airport ids to optimize path search
        MATCH()-[:DELIVERY {legId:incomingLegId}]->(n:TransferPoint)
        WITH incomingLegId, shipmentId, n.airportId AS transferAirportId

        //incoming path
        MATCH p=(:EntryPoint {airportId: $sourceAirportId})-[*1..12 {legId: incomingLegId}]->(:TransferPoint {airportId: transferAirportId})
        WITH incomingLegId, shipmentId, transferAirportId, nodes(p) AS n, relationships(p) AS r
        WITH incomingLegId, shipmentId, transferAirportId,
           apoc.text.join([i IN range(1,size(n)) WHERE (i=1) OR (n[i].airportId <> n[i-1].airportId )| n[i].name], ' -> ') AS incomingAirports,
           reduce(s=0, i in r | s + i.effectiveMinutes ) AS incomingCost

        //outgoing path (leg numbers are -1)
        MATCH p=(:TransferPoint {airportId: transferAirportId})-[*1..12 {shipmentId: shipmentId, legNumber:-1}]->(:Destination {airportId: $targetAirportId})
        WITH incomingLegId, incomingAirports, incomingCost, nodes(p) AS n, relationships(p) AS r
        WITH incomingLegId, incomingAirports,
            incomingAirports + ' -> ' + apoc.text.join([i IN range(1,size(n)) WHERE n[i].airportId <> n[i-1].airportId | n[i].name], ' -> ')  AS airportPath,
            incomingCost + reduce(s=0, i in r | s + i.effectiveMinutes  ) AS totalCost

        //aggregate and return
        RETURN DISTINCT airportPath, size(collect(incomingLegId)) AS historicPathCount, avg(totalCost) AS historicAvgCostMin, stDev(totalCost) AS historicCostStdMin, collect(totalCost) AS historicCostsMin
        ORDER BY historicPathCount DESC
    ''', params={'sourceAirportId': sid, 'targetAirportId': tid})

    df['historicAvgCost'] = minutes_to_duration(df.historicAvgCostMin)
    df['historicCostStd'] = minutes_to_duration(df.historicCostStdMin)
    df['historicCosts'] = minutes_to_duration_arr_col(df.historicCostsMin)
    df.drop(columns=['historicAvgCostMin', 'historicCostStdMin', 'historicCostsMin'], inplace=True)
    return df


def get_yen_dfs(gds, g, source_node_ids, target_node_ids, k, max_avg_time=np.Inf):
    df_list = []
    for source_node_id in source_node_ids:
        for target_node_id in target_node_ids:
            tdf = gds.shortestPath.yens.stream(g, sourceNode=source_node_id, targetNode=target_node_id,
                                               k=k, relationshipWeightProperty='averageEffectiveMinutes')
            if max_avg_time < np.Inf:
                tdf = tdf[tdf.totalCost <= max_avg_time]
            df_list.append(tdf)
    return df_list


def get_solution_costs(row, path_dfs):
    solution = row.solutionIndex
    rels = {}
    path_costs = []
    for n in range(len(solution)):
        path_costs.append(path_dfs[n].totalCost[solution[n]])
        for r in path_dfs[n].path[solution[n]].relationships:
            rels[f'{r.start_node.id}-{r.end_node.id}'] = r
    return sum([r.get('cost') for r in rels.values()]), path_costs, list(rels.values())


def top_k_solutions(gds, g, source_node_ids, target_node_ids, top_k=10, yen_candidates=10, max_avg_time=np.Inf):
    # get paths
    path_dfs = get_yen_dfs(gds, g, source_node_ids, target_node_ids, yen_candidates, max_avg_time)
    # get solutions
    solution_df = pd.DataFrame(itertools.product(*[range(path_df.shape[0]) for path_df in path_dfs])) \
        .apply(tuple, axis=1).to_frame(name='solutionIndex')
    solution_df[['totalCost', 'pathCosts', 'relationships']] = solution_df.apply(get_solution_costs,
                                                                                 args=([path_dfs]), axis=1,
                                                                                 result_type='expand')
    # return top solutions
    return solution_df.sort_values('totalCost')[:top_k].reset_index(drop=True)


def top_k_solutions_from_names(gds, g, source_airport_names, target_airport_name, top_k=10, yen_candidates=10,
                               max_avg_time=np.Inf):
    source_node_ids = [gds.find_node_id(['EntryPoint'], {'name': i}) for i in source_airport_names]
    target_node_ids = [gds.find_node_id(['Destination'], {'name': target_airport_name})]
    return top_k_solutions(gds, g, source_node_ids, target_node_ids, top_k=top_k, yen_candidates=yen_candidates,
                           max_avg_time=max_avg_time)


def top_k_solutions_from_airport_ids(gds, g, source_airport_ids, target_airport_id, top_k=10, yen_candidates=10,
                                     max_avg_time=np.Inf):
    source_node_ids = [gds.find_node_id(['EntryPoint'], {'airportId': i}) for i in source_airport_ids]
    target_node_ids = [gds.find_node_id(['Destination'], {'airportId': target_airport_id})]
    return top_k_solutions(gds, g, source_node_ids, target_node_ids, top_k=top_k, yen_candidates=yen_candidates,
                           max_avg_time=max_avg_time)


def format_nodes_and_rels(relationships):
    records = []
    for r in relationships:
        records.append({'sourceNodeId': r.start_node.id, 'targetNodeId': r.end_node.id, 'cost': r.get('cost')})
    rel_df = pd.DataFrame.from_records(records)
    return pd.DataFrame(set(rel_df.sourceNodeId).union(rel_df.targetNodeId), columns=['nodeId']), rel_df


def remove_solution_from_db(gds, solution_tag, solution_tag_name='solutionTag', rel_type='SOLUTION_PATH'):
    gds.run_cypher(f'MATCH()-[r:{rel_type}]->() WHERE {solution_tag_name} = "{solution_tag}" DELETE r')


def remove_solution_type_from_db(gds, solution_tag_name='solutionTag', rel_type='SOLUTION_PATH'):
    gds.run_cypher(f'MATCH()-[r:{rel_type}]->() DELETE r')
    gds.run_cypher(f'DROP INDEX {rel_type.lower()}_{solution_tag_name}_index IF EXISTS')


def write_solution_to_db(gds, relationships, solution_tag, solution_tag_name='solutionTag', rel_type='SOLUTION_PATH'):
    _, rels_df = format_nodes_and_rels(relationships)

    gds.run_cypher(f'''
        CREATE INDEX {rel_type.lower()}_{solution_tag_name}_index 
        IF NOT EXISTS FOR ()-[r:{rel_type}]-() 
        ON (r.{solution_tag_name})
    ''')

    gds.run_cypher(f'''
        UNWIND $rels AS rels
        WITH toInteger(rels.sourceNodeId) AS sourceNodeId,
            toInteger(rels.targetNodeId) AS targetNodeId,
            rels.cost AS cost
        MATCH(n1) WHERE id(n1) = sourceNodeId
        MATCH(n2) WHERE id(n2) = targetNodeId
        MERGE(n1)-[r:{rel_type} {{{solution_tag_name}:"{solution_tag}"}}]->(n2)
        SET r.cost=cost
    ''', params={'rels': rels_df.to_dict('records')})
