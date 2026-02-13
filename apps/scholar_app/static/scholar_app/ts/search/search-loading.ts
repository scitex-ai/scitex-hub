/**
 * Search Loading Display Module
 *
 * Shows inspiring quotes during search loading instead of a generic spinner.
 */

// Curated quotes for search loading display (53 quotes across themes)
const SEARCH_QUOTES = [
  // Discovery & Research
  {
    text: "If I have seen further, it is by standing on the shoulders of giants.",
    author: "Isaac Newton",
  },
  {
    text: "Research is to see what everybody else has seen, and to think what nobody else has thought.",
    author: "Albert Szent-Györgyi",
  },
  {
    text: "The most exciting phrase in science is not 'Eureka!' but 'That's funny...'",
    author: "Isaac Asimov",
  },
  {
    text: "If we knew what we were doing, it would not be called research.",
    author: "Albert Einstein",
  },
  {
    text: "In the fields of observation, chance favors only the prepared mind.",
    author: "Louis Pasteur",
  },
  {
    text: "Nothing has such power to broaden the mind as the ability to investigate systematically.",
    author: "Marcus Aurelius",
  },
  {
    text: "Science does not know its debt to imagination.",
    author: "Ralph Waldo Emerson",
  },
  {
    text: "Imagination is more important than knowledge.",
    author: "Albert Einstein",
  },
  {
    text: "Every great advance in science has issued from a new audacity of imagination.",
    author: "John Dewey",
  },
  {
    text: "It is through science that we prove, but through intuition that we discover.",
    author: "Henri Poincaré",
  },
  {
    text: "The outcome of any serious research can only be to make two questions grow where only one grew before.",
    author: "Thorstein Veblen",
  },
  {
    text: "If you want to have good ideas, you must have many ideas.",
    author: "Linus Pauling",
  },
  {
    text: "Equipped with his five senses, man explores the universe around him and calls the adventure Science.",
    author: "Edwin Hubble",
  },
  {
    text: "Somewhere, something incredible is waiting to be known.",
    author: "Carl Sagan",
  },
  {
    text: "Science is not only a disciple of reason but also one of romance and passion.",
    author: "Stephen Hawking",
  },
  {
    text: "Science and everyday life cannot and should not be separated.",
    author: "Rosalind Franklin",
  },
  {
    text: "Advances are made by answering questions. Discoveries are made by questioning answers.",
    author: "Bernard Haisch",
  },
  {
    text: "No research without action, no action without research.",
    author: "Kurt Lewin",
  },
  {
    text: "The process of scientific discovery is, in effect, a continual flight from wonder.",
    author: "Albert Einstein",
  },
  // Data & Knowledge
  {
    text: "It is a capital mistake to theorize before one has data.",
    author: "Arthur Conan Doyle",
  },
  {
    text: "The saddest aspect of life is that science gathers knowledge faster than society gathers wisdom.",
    author: "Isaac Asimov",
  },
  {
    text: "Nothing in life is to be feared, it is only to be understood.",
    author: "Marie Curie",
  },
  {
    text: "Without data, you're just another person with an opinion.",
    author: "W. Edwards Deming",
  },
  {
    text: "What we know is a drop, what we don't know is an ocean.",
    author: "Isaac Newton",
  },
  {
    text: "The good thing about science is that it's true whether or not you believe in it.",
    author: "Neil deGrasse Tyson",
  },
  {
    text: "What you learn from a life in science is the vastness of our ignorance.",
    author: "David Eagleman",
  },
  // Humor
  {
    text: "The great tragedy of science — the slaying of a beautiful hypothesis by an ugly fact.",
    author: "Thomas Huxley",
  },
  {
    text: "I have had my results for a long time, but I do not yet know how I am to arrive at them.",
    author: "Gauss",
  },
  {
    text: "If you torture the data long enough, it will confess.",
    author: "Ronald Coase",
  },
  {
    text: "Basic research is what I am doing when I don't know what I am doing.",
    author: "Wernher von Braun",
  },
  {
    text: "It is a good morning exercise for a research scientist to discard a pet hypothesis every day before breakfast.",
    author: "Konrad Lorenz",
  },
  {
    text: "Science is a wonderful thing if one does not have to earn one's living at it.",
    author: "Albert Einstein",
  },
  // Literature & Reading
  {
    text: "One glance at a book and you hear the voice of another person, perhaps someone dead for 1,000 years.",
    author: "Carl Sagan",
  },
  {
    text: "Reading furnishes the mind only with materials of knowledge; it is thinking that makes what we read ours.",
    author: "John Locke",
  },
  {
    text: "I have always imagined that Paradise will be a kind of library.",
    author: "Jorge Luis Borges",
  },
  {
    text: "Books are the carriers of civilization. Without books, history is silent, literature dumb, science crippled.",
    author: "Barbara W. Tuchman",
  },
  {
    text: "Books serve to show a man that those original thoughts of his aren't very new after all.",
    author: "Abraham Lincoln",
  },
  {
    text: "Google can bring you back 100,000 answers. A librarian can bring you back the right one.",
    author: "Neil Gaiman",
  },
  {
    text: "A classic is a book that has never finished saying what it has to say.",
    author: "Italo Calvino",
  },
  {
    text: "A capacity and taste for reading gives access to whatever has already been discovered by others.",
    author: "Abraham Lincoln",
  },
  {
    text: "Books have a unique way of stopping time in a particular moment and saying: Let's not forget this.",
    author: "Dave Eggers",
  },
  // Time & Patience
  {
    text: "The two most powerful warriors are patience and time.",
    author: "Leo Tolstoy",
  },
  {
    text: "Adopt the pace of nature: her secret is patience.",
    author: "Ralph Waldo Emerson",
  },
  { text: "Time is the wisest counselor of all.", author: "Pericles" },
  {
    text: "It does not matter how slowly you go as long as you do not stop.",
    author: "Confucius",
  },
  {
    text: "Great works are performed not by strength but by perseverance.",
    author: "Samuel Johnson",
  },
  {
    text: "Patience is bitter, but its fruit is sweet.",
    author: "Jean-Jacques Rousseau",
  },
  {
    text: "With time and patience, the mulberry leaf becomes silk.",
    author: "Chinese Proverb",
  },
  {
    text: "Great things are not done by impulse, but by a series of small things brought together.",
    author: "Vincent van Gogh",
  },
  {
    text: "Have patience. All things are difficult before they become easy.",
    author: "Saadi",
  },
  {
    text: "The bad news is time flies. The good news is you're the pilot.",
    author: "Michael Altshuler",
  },
  {
    text: "I am a slow walker, but I never walk back.",
    author: "Abraham Lincoln",
  },
  {
    text: "Don't watch the clock; do what it does. Keep going.",
    author: "Sam Levenson",
  },
];

/**
 * Get a random quote
 */
function getRandomQuote(): { text: string; author: string } {
  return SEARCH_QUOTES[Math.floor(Math.random() * SEARCH_QUOTES.length)];
}

/**
 * Generate the loading HTML with a random quote and blur reveal animation
 */
export function getLoadingHtml(): string {
  const quote = getRandomQuote();
  return `
    <div class="search-loading" style="
      text-align: center;
      padding: 2.5rem 1.5rem;
      color: var(--text-muted, #6c8ba0);
    ">
      <style>
        @keyframes blurReveal {
          0% {
            filter: blur(12px);
            opacity: 0;
            transform: translateX(-30px);
          }
          100% {
            filter: blur(0);
            opacity: 1;
            transform: translateX(0);
          }
        }
        @keyframes blurOut {
          0% {
            filter: blur(0);
            opacity: 1;
            transform: translateX(0);
          }
          100% {
            filter: blur(12px);
            opacity: 0;
            transform: translateX(30px);
          }
        }
        .quote-reveal {
          animation: blurReveal 0.8s ease-out forwards;
        }
        .quote-exit {
          animation: blurOut 0.5s ease-in forwards;
        }
      </style>
      <i class="fas fa-search" style="font-size: 1.5rem; margin-bottom: 1rem; opacity: 0.4; display: block;"></i>
      <div id="quoteContainer" class="quote-reveal" style="
        max-width: 520px;
        margin: 0 auto;
      ">
        <blockquote id="quoteText" style="
          font-style: italic;
          font-size: 1.1rem;
          margin: 0 0 0.75rem;
          line-height: 1.6;
          color: var(--text-secondary, #9ca3af);
          min-height: 2em;
        ">"${quote.text}"</blockquote>
        <cite id="quoteAuthor" style="
          font-size: 0.85rem;
          color: var(--text-muted, #6c8ba0);
          display: block;
        ">— ${quote.author}</cite>
      </div>
    </div>
  `;
}

/**
 * Animate to a new quote with blur transition
 */
function animateToNewQuote(quote: { text: string; author: string }): void {
  const containerEl = document.getElementById("quoteContainer");
  const quoteEl = document.getElementById("quoteText");
  const authorEl = document.getElementById("quoteAuthor");
  if (!containerEl || !quoteEl || !authorEl) return;

  // Exit animation on container
  containerEl.className = "quote-exit";

  // After exit, update content and reveal
  setTimeout(() => {
    quoteEl.textContent = `"${quote.text}"`;
    authorEl.textContent = `— ${quote.author}`;
    containerEl.className = "quote-reveal";
  }, 500);
}

// Track quote rotation interval
let quoteRotationInterval: ReturnType<typeof setInterval> | null = null;
let usedQuoteIndices: number[] = [];

/**
 * Get a random quote that hasn't been shown recently
 */
function getUniqueRandomQuote(): { text: string; author: string } {
  if (usedQuoteIndices.length >= SEARCH_QUOTES.length - 1) {
    usedQuoteIndices = []; // Reset when most quotes used
  }

  let index: number;
  do {
    index = Math.floor(Math.random() * SEARCH_QUOTES.length);
  } while (usedQuoteIndices.includes(index));

  usedQuoteIndices.push(index);
  return SEARCH_QUOTES[index];
}

/**
 * Show a new quote with blur transition
 */
function showNextQuote(): void {
  const quote = getUniqueRandomQuote();
  animateToNewQuote(quote);
}

/**
 * Show loading state in the progressive results container
 */
export function showSearchLoading(): void {
  const progressiveResults = document.getElementById("progressiveResults");
  if (progressiveResults) {
    progressiveResults.style.display = "block";
    progressiveResults.innerHTML = getLoadingHtml();

    // Rotate quotes every 7 seconds
    quoteRotationInterval = setInterval(() => {
      const loadingEl = document.querySelector(".search-loading");
      if (loadingEl) {
        showNextQuote();
      } else {
        // Stop if loading element removed
        if (quoteRotationInterval) {
          clearInterval(quoteRotationInterval);
          quoteRotationInterval = null;
        }
      }
    }, 7000);
  }
}

/**
 * Hide loading state
 */
export function hideSearchLoading(): void {
  if (quoteRotationInterval) {
    clearInterval(quoteRotationInterval);
    quoteRotationInterval = null;
  }
  usedQuoteIndices = [];

  const loadingEl = document.querySelector(".search-loading");
  if (loadingEl) {
    loadingEl.remove();
  }
}
