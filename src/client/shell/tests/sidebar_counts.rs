use super::*;

fn counted_snapshot(spaces: usize, agents: usize) -> ClientShellSnapshot {
    let mut projected = snapshot();
    let workspace = projected.workspaces[0].clone();
    projected.workspaces = (0..spaces)
        .map(|index| {
            let mut workspace = workspace.clone();
            workspace.workspace_id = format!("ws_{}", index + 1);
            workspace.number = index + 1;
            workspace.focused = index == 0;
            workspace
        })
        .collect();
    projected.agents = (0..agents)
        .map(|index| ClientShellAgent {
            pane_id: format!("pane_{}", index + 1),
            workspace_id: "ws_1".into(),
            tab_id: "tab_1".into(),
            name: Some("test".into()),
            display_agent: None,
            agent: Some("pi".into()),
            title: None,
            terminal_title: None,
            terminal_title_stripped: None,
            agent_status: AgentStatus::Idle,
            state_change_seq: 1,
            state_labels: Vec::new(),
            tokens: Vec::new(),
            focused: index == 0,
        })
        .collect();
    projected
}

#[test]
fn sidebar_counts_follow_additions_removals_and_empty_lists() {
    let mut state = ClientShellState::new(ClientShellConfig::from_config(&Config::default()));
    for (revision, (spaces, agents)) in [(1, 0), (5, 14), (2, 3), (0, 0)].into_iter().enumerate() {
        let mut projected = counted_snapshot(spaces, agents);
        projected.revision = revision as u64 + 1;
        state.set_snapshot(Box::new(projected));
        let frame = state.compose(106, 24).expect("sidebar frame");
        let text = frame_rows(&frame).join("\n");
        assert!(text.contains(&format!("spaces ({spaces})")), "{text}");
        assert!(text.contains(&format!("agents ({agents})")), "{text}");
    }
}

#[test]
fn sidebar_counts_can_be_hidden_independently() {
    for (spaces, agents) in [(false, true), (true, false), (false, false)] {
        let mut config = Config::default();
        config.ui.sidebar.spaces.show_count = spaces;
        config.ui.sidebar.agents.show_count = agents;
        let mut state = ClientShellState::new(ClientShellConfig::from_config(&config));
        state.set_snapshot(Box::new(counted_snapshot(5, 14)));
        let frame = state.compose(106, 24).expect("sidebar frame");
        let text = frame_rows(&frame).join("\n");
        assert_eq!(text.contains("spaces (5)"), spaces, "{text}");
        assert_eq!(text.contains("agents (14)"), agents, "{text}");
    }
}

#[test]
fn sidebar_counts_follow_filtered_agent_view() {
    let mut state = ClientShellState::new(ClientShellConfig::from_config(&Config::default()));
    let mut projected = counted_snapshot(5, 14);
    projected.agent_view_label = Some("current space".into());
    projected.agent_order = vec!["pane_1".into(), "pane_3".into()];
    state.set_snapshot(Box::new(projected));
    let frame = state.compose(106, 24).expect("filtered frame");
    let text = frame_rows(&frame).join("\n");
    assert!(text.contains("agents (2)"), "{text}");
}

#[test]
fn sidebar_counts_keep_agent_heading_and_sort_hit_separate_at_narrow_widths() {
    let config = ClientShellConfig::from_config(&Config::default());
    for width in [0, 8, 12, 18, 26] {
        let area = Rect::new(0, 0, width, 4);
        let mut buffer = Buffer::empty(area);
        let mut hits = ShellHitMap::default();
        super::super::agent_sidebar::render_agent_panel_header(
            &mut buffer,
            area,
            None,
            14,
            &config,
            &mut hits,
        );
        if width >= 12 {
            let text = (0..width)
                .map(|x| buffer[(x, 1)].symbol())
                .collect::<String>();
            assert!(text.starts_with(" agents (14)"), "{text}");
            if hits.agent_sort_toggle.width > 0 {
                assert!(hits.agent_sort_toggle.x >= 13);
            }
        }
        assert!(hits.agent_sort_toggle.right() <= width);
    }
}
