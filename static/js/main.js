document.addEventListener('DOMContentLoaded', function() {
    // Form validation
    const subscribeForm = document.getElementById('subscribeForm');
    if (subscribeForm) {
        subscribeForm.addEventListener('submit', function(e) {
            const email = document.getElementById('email').value;
            if (!email || !email.includes('@')) {
                e.preventDefault();
                alert('Please enter a valid email address!');
            }
        });
    }

    // Flash message animation
    const flashMessages = document.querySelectorAll('.flash-message');
    flashMessages.forEach(message => {
        setTimeout(() => {
            message.style.opacity = '0';
            message.style.transition = 'opacity 0.5s';
        }, 3000);
    });

    // Admin joke form character counter
    const jokeContent = document.getElementById('jokeContent');
    const charCounter = document.getElementById('charCounter');
    if (jokeContent && charCounter) {
        jokeContent.addEventListener('input', function() {
            charCounter.textContent = `${this.value.length}/500`;
        });
    }
});
