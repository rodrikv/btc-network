import plotly.graph_objects as go

import random


class NetworkPlot:
    def edge_trace(self, nodes):
        edge_x = []
        edge_y = []
        hover_text = []
        for addr, node in nodes.items():
            for out in node['outs']:
                x0, y0 = node['pos']
                x1, y1 = nodes[str(out)]['pos']
                edge_x.append(x0)
                edge_x.append(x1)
                edge_x.append(None)
                edge_y.append(y0)
                edge_y.append(y1)
                edge_y.append(None)
                hover_text.append(f'from {addr} to {str(out)}')
        edge_trace = go.Scatter(
            x=edge_x, y=edge_y,
            line=dict(width=0.5, color='#888'),
            hoverinfo='text',
            hovertext=hover_text,
            mode='lines')
        return edge_trace

    def put_arrows(self, fig, nodes):
        for addr, node in nodes.items():
            x0, y0 = node['pos']
            for out in node['outs']:
                x1, y1 = nodes[str(out)]['pos']
                ay = y1-y0
                ax = x1-x0
                fig.add_annotation(
                    x=x0, y=y0,
                    xref="x", yref="y",
                    text='',
                    showarrow=True,
                    font=dict(
                        family="Courier New, monospace", size=2, color='red'
                    ),
                    align="center",
                    arrowhead=1, arrowsize=1, arrowwidth=1, arrowcolor="#636363",
                    ax=ax, ay=ay,
                    borderpad=2,
                    bgcolor='black',
                    opacity=0.3,
                    # Place in the chart
                )

        return fig

    def node_trace(self, nodes):
        node_x = []
        node_y = []
        for node in nodes.values():
            x, y = node['pos']
            node_x.append(x)
            node_y.append(y)

        node_trace = go.Scatter(
            x=node_x, y=node_y,
            mode='markers',
            hoverinfo='text',
            marker=dict(
                showscale=True,
                # colorscale options
                # 'Greys' | 'YlGnBu' | 'Greens' | 'YlOrRd' | 'Bluered' | 'RdBu' |
                # 'Reds' | 'Blues' | 'Picnic' | 'Rainbow' | 'Portland' | 'Jet' |
                # 'Hot' | 'Blackbody' | 'Earth' | 'Electric' | 'Viridis' |
                colorscale='YlGnBu',
                reversescale=True,
                color=[],
                size=10,
                colorbar=dict(
                    thickness=15,
                    title='Node Connections',
                    xanchor='left',
                    titleside='right'
                ),
                line_width=2))

        node_adjacencies = []
        node_text = []
        for ip, node in nodes.items():
            node_adjacencies.append(len(node["outs"]) + len(node["ins"]))
            node_text.append(
                f'#{len(node["outs"])}outs #{len(node["ins"])}ins <{ip}> name: {node["name"]}')

        node_trace.marker.color = node_adjacencies
        node_trace.text = node_text

        return node_trace

    def __manipulate_nodes(self, nodes):
        new_nodes = {}
        for node in nodes:
            new_nodes[str(node.id)] = {
                'pos': (random.random(), random.random()),
                'outs': node.outs,
                'ins': node.ins,
                'name': node.name,
            }
        return new_nodes

    def plot(self, nodes):
        nodes = self.__manipulate_nodes(nodes)
        edge_trace = self.edge_trace(nodes)
        node_trace = self.node_trace(nodes)
        fig = go.Figure(data=[edge_trace, node_trace],
                        layout=go.Layout(
                        title='<b>BITCOIN SIMULATED NETWORK GRAPH</b>',
                        titlefont_size=16,
                        showlegend=False,
                        hovermode='closest',
                        margin=dict(b=20, l=5, r=5, t=40),
                        annotations=[dict(
                            showarrow=False,
                            xref="paper", yref="paper",
                            x=0.005, y=-0.002)],
                        xaxis=dict(showgrid=False, zeroline=False,
                                   showticklabels=False),
                        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False))
                        )
        fig.write_html("graph.html")
        fig.show()
