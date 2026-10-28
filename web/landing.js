window.mountSystem1BenchLanding = function mountSystem1BenchLanding(root = document) {
  const dialog = root.querySelector('#lp-legal-dialog');
  if (!dialog || dialog.dataset.mounted) return;
  dialog.dataset.mounted = 'true';
  const title = dialog.querySelector('#lp-legal-title');
  const copy = dialog.querySelector('#lp-legal-copy');
  const paragraphs = [
    'System 1 Bench tests quick intuition across different categories. The first test, Internet instinct, asks you to pick the X post that received more views. Two unscored practice rounds with feedback come first, then 15 scored pairs. You have three seconds to look, then two seconds to choose.',
    'The real test is an early pilot using pairs from the same author. Its pool comes from keyword searches and uses cumulative views captured at collection time. Human and AI comparisons will follow real benchmark runs.',
    'No account is needed. Answers and timings are saved anonymously. A browser cookie keeps repeat attempts out of the pilot comparison. This prototype adds no analytics or advertising trackers. The hosting provider may process ordinary request information to serve the page.',
    'System 1 Bench is experimental. Pilot scores describe this question set. X posts belong to their authors, who do not endorse this test.'
  ];
  root.querySelectorAll('[data-legal="about"]').forEach(button => {
    button.addEventListener('click', () => {
      title.textContent = 'About System 1 Bench';
      copy.replaceChildren(...paragraphs.map(text => {
        const p = document.createElement('p');
        p.textContent = text;
        return p;
      }));
      dialog.showModal();
    });
  });
  root.querySelectorAll('[data-close-dialog]').forEach(button => button.addEventListener('click', () => dialog.close()));
  dialog.addEventListener('click', event => {
    const bounds = dialog.getBoundingClientRect();
    const outside = event.clientX < bounds.left || event.clientX > bounds.right || event.clientY < bounds.top || event.clientY > bounds.bottom;
    if (event.target === dialog && outside) dialog.close();
  });
};
window.mountSystem1BenchLanding();
