// ============================================================
// recommend.js — MoE Recommendation Engine Display
// ============================================================

async function loadRecommendations() {
    const container = document.getElementById('recommendedVideos');
    if (!container) return;

    container.innerHTML = `
        <div class="col-12 text-center py-4">
            <div class="spinner-border"
                 style="width:2rem; height:2rem; color:#7c3aed;"></div>
            <p class="mt-3 text-muted" style="font-size:0.82rem;">
                🤖 MoE AI analyzing your profile...
            </p>
        </div>`;

    const data = await API.get('/recommend/videos');

    console.log('MoE Response:', data);

    if (!data.success || !data.recommendations ||
        !data.recommendations.length) {
        container.innerHTML = `
            <div class="col-12 text-center py-4">
                <div style="font-size:2.5rem; margin-bottom:10px;">
                    🤖
                </div>
                <p class="text-muted" style="font-size:0.85rem;">
                    Search a topic above to get AI recommendations!
                </p>
            </div>`;
        return;
    }

    // Expert styling
    const expertStyle = {
        'weak_topic' : {
            bg   : '#fef2f2',
            color: '#dc2626',
            label: '⚠️ Weak Topic'
        },
        'cognitive'  : {
            bg   : '#eff6ff',
            color: '#2563eb',
            label: '🧠 Cognitive'
        },
        'history'    : {
            bg   : '#faf5ff',
            color: '#7c3aed',
            label: '📺 New Topic'
        },
        'performance': {
            bg   : '#f0fdf4',
            color: '#059669',
            label: '📊 Performance'
        }
    };

    container.innerHTML = data.recommendations.map(v => {
        const titleJson  = JSON.stringify(v.title  || '');
        const reasonJson = JSON.stringify(v.reason || '');
        const es         = expertStyle[v.expert] ||
                           {bg:'#f8fafc', color:'#64748b', label:'🎯 AI'};
        const matchPct   = v.final_score ?
                           Math.round(v.final_score * 100) : 0;

        return `
        <div class="col-md-3 col-sm-6 mb-3">
            <div class="vid-card"
                 onclick='openVideo(
                     "${v.video_id}",
                     ${titleJson},
                     ${reasonJson}
                 )'>
                <div class="vid-thumb">
                    <img src="${v.thumbnail}"
                         alt="video"
                         onerror="this.src='https://via.placeholder.com/320x180?text=Video'">
                    <div class="vid-overlay">
                        <div class="vid-play-btn">
                            <i class="fas fa-play"></i>
                        </div>
                    </div>

                    <!-- Expert Badge -->
                    <div style="position:absolute; top:7px; left:7px;
                                background:${es.bg};
                                color:${es.color};
                                border:1px solid ${es.color}33;
                                padding:2px 8px;
                                border-radius:10px;
                                font-size:0.62rem;
                                font-weight:700;
                                backdrop-filter:blur(4px);">
                        ${es.label}
                    </div>

                    <!-- Match Score -->
                    ${matchPct > 0 ? `
                    <div style="position:absolute; bottom:7px; right:7px;
                                background:rgba(0,0,0,0.75);
                                color:white;
                                padding:2px 7px;
                                border-radius:6px;
                                font-size:0.62rem;
                                font-weight:600;">
                        ${matchPct}% match
                    </div>` : ''}
                </div>

                <div class="vid-info">
                    <p class="vid-title">
                        ${(v.title || '').substring(0, 60)}
                        ${(v.title || '').length > 60 ? '...' : ''}
                    </p>
                    <div style="display:flex;
                                justify-content:space-between;
                                align-items:center;
                                flex-wrap:wrap; gap:4px;">
                        <span class="vid-tag">
                            ${v.channel || 'YouTube'}
                        </span>
                    </div>
                    <!-- Reason -->
                    <div style="font-size:0.68rem;
                                color:#94a3b8;
                                margin-top:5px;
                                line-height:1.3;
                                display:-webkit-box;
                                -webkit-line-clamp:2;
                                -webkit-box-orient:vertical;
                                overflow:hidden;">
                        ${v.reason || ''}
                    </div>
                </div>
            </div>
        </div>`;
    }).join('');
}
