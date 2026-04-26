flowchart TD
    subgraph INPUT["Inputs"]
        direction TB
        CSV[(songs.csv)]
        PROFILE["Built-in Profile\nalex / maya / ryan"]
        CUSTOM["Custom Personality\nStreamlit Sliders"]
        AI_FETCH["AI Song Fetcher\nai_songs.py · Gemini"]
        SP_FETCH["Spotify Fetcher\nfetch_songs.py"]
    end

    AI_FETCH -->|new songs appended| CSV
    SP_FETCH -->|new songs appended| CSV

    subgraph WORKFLOW["Agentic Recommendation Workflow"]
        direction TB
        PA["Profile Agent\nresolves user preferences"]
        PLA["Planner Agent\nGemini — picks mode, top_k, penalty\nFallback: local logic"]
        RA["Ranking Agent\nweighted feature scoring"]
        QA["Quality Check Agent\nGemini — checks diversity + scores\nFallback: local logic"]
        LRA["Link Routing Agent\nbuilds search URLs"]
    end

    PROFILE --> PA
    CUSTOM  --> PA
    CSV     --> RA
    PA      -->|user prefs| PLA
    PLA     -->|strategy| RA
    RA      -->|ranked songs| QA
    QA -->|"quality_pass=False → revised strategy"| RA
    QA -->|"quality_pass=True"| LRA

    subgraph OUTPUT["Output"]
        direction TB
        UI["Streamlit UI\nsong cards · feature chart · agent report"]
        CLI["CLI Table\n--show-agent-log"]
        BROWSER["Browser\n--open-browser"]
    end

    LRA --> UI
    LRA --> CLI
    CLI -->|user selects a link| BROWSER

    classDef gemini fill:#1a3a6b,stroke:#4d9fff,color:#c8e0ff,stroke-width:2px
    classDef agent  fill:#0d1f3c,stroke:#2a5fa8,color:#a8caff,stroke-width:1px
    classDef data   fill:#0a1628,stroke:#1e4080,color:#8ab4f8,stroke-width:1px
    classDef output fill:#061020,stroke:#1a3a6b,color:#7aaaf0,stroke-width:1px
    classDef fetch  fill:#0d2b1e,stroke:#1e7a4a,color:#7af0b0,stroke-width:1px

    class PLA,QA gemini
    class PA,RA,LRA agent
    class CSV,PROFILE,CUSTOM data
    class UI,CLI,BROWSER output
    class AI_FETCH,SP_FETCH fetch
