// Cargar datos del dashboard
async function loadDashboardData() {
    try {
        // Cargar estado Free Tier
        const freeTierResponse = await fetch('/api/free-tier-status');
        const freeTierData = await freeTierResponse.json();
        
        // Actualizar tarjetas
        document.getElementById('free-tier-remaining').textContent = `$${freeTierData.free_tier_remaining}`;
        document.getElementById('free-tier-used').textContent = `$${freeTierData.monthly_cost} usados`;
        document.getElementById('monthly-cost').textContent = `$${freeTierData.monthly_cost.toFixed(2)}`;
        document.getElementById('alerts-count').textContent = freeTierData.alerts.length;
        
        // Cargar recomendaciones EC2
        const ec2Response = await fetch('/api/ec2-recommendations');
        const ec2Data = await ec2Response.json();
        document.getElementById('ec2-count').textContent = ec2Data.total_recommendations;
        document.getElementById('ec2-recommendations').textContent = `${ec2Data.total_recommendations} recomendaciones`;
        
        // Cargar datos de costos para gráficos
        const costResponse = await fetch('/api/cost-overview?days=7');
        const costData = await costResponse.json();
        
        // Renderizar gráficos
        renderCharts(costData);
        renderRecommendations(ec2Data);
        
    } catch (error) {
        console.error('Error loading dashboard data:', error);
    }
}

// Renderizar gráficos
function renderCharts(costData) {
    // Gráfico de distribución (usando datos de ejemplo)
    const distributionCtx = document.getElementById('costDistributionChart').getContext('2d');
    new Chart(distributionCtx, {
        type: 'doughnut',
        data: {
            labels: ['EC2', 'S3', 'RDS', 'Lambda', 'Otros'],
            datasets: [{
                data: [45, 25, 15, 10, 5],
                backgroundColor: ['#007bff', '#28a745', '#ffc107', '#dc3545', '#6c757d']
            }]
        }
    });
    
    // Gráfico de tendencia (usando datos de ejemplo)
    const trendCtx = document.getElementById('costTrendChart').getContext('2d');
    new Chart(trendCtx, {
        type: 'line',
        data: {
            labels: ['Day 1', 'Day 2', 'Day 3', 'Day 4', 'Day 5', 'Day 6', 'Day 7'],
            datasets: [{
                label: 'Costo Diario',
                data: [0.85, 1.20, 0.95, 1.50, 0.75, 1.10, 0.90],
                borderColor: '#007bff',
                backgroundColor: 'rgba(0, 123, 255, 0.1)'
            }]
        }
    });
}

// Renderizar recomendaciones
function renderRecommendations(ec2Data) {
    const container = document.getElementById('recommendations-list');
    
    if (ec2Data.recommendations && ec2Data.recommendations.length > 0) {
        container.innerHTML = ec2Data.recommendations.map(rec => `
            <div class="recommendation-item">
                <h6><i class="fas fa-server"></i> ${rec.instance_id}</h6>
                <p><strong>Recomendación:</strong> ${rec.recommendation}</p>
                <small class="text-muted">Ahorro estimado: ${rec.savings_estimate}</small>
            </div>
        `).join('');
    } else {
        container.innerHTML = `
            <div class="alert alert-success">
                <i class="fas fa-check-circle"></i> ¡Excelente! No se encontraron recomendaciones críticas.
            </div>
        `;
    }
}

// Cargar datos cuando la página esté lista
document.addEventListener('DOMContentLoaded', loadDashboardData);