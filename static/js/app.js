document.addEventListener('DOMContentLoaded', function() {
    // Auto-dismiss flash messages after 5s
    document.querySelectorAll('.flash').forEach(function(el) {
        setTimeout(function() {
            el.style.opacity = '0';
            el.style.transform = 'translateY(-10px)';
            el.style.transition = 'all 0.3s';
            setTimeout(function() { el.remove(); }, 300);
        }, 5000);
    });

    // Animate result bars on scroll
    var bars = document.querySelectorAll('.bar-fill[data-width]');
    if (bars.length > 0) {
        setTimeout(function() {
            bars.forEach(function(bar) {
                bar.style.width = bar.getAttribute('data-width');
            });
        }, 300);
    }
});
