/* ------------------------------------------------------------ *
 *  Mermaid extras for MkDocs Material - Fixed Pan-Zoom         *
 * ------------------------------------------------------------ */

// Load svg-pan-zoom library immediately
(function() {
  if (typeof svgPanZoom === 'undefined') {
    const script = document.createElement('script');
    script.src = 'https://cdn.jsdelivr.net/npm/svg-pan-zoom@3.6.1/dist/svg-pan-zoom.min.js';
    script.async = false;
    document.head.appendChild(script);
  }
})();

console.log('🚀 Mermaid extras script loaded');

// Initialize when ready
function whenReady(fn) {
  if (typeof document$ !== 'undefined') {
    // Material for MkDocs
    document$.subscribe(fn);
  } else if (document.readyState !== 'loading') {
    fn();
  } else {
    document.addEventListener('DOMContentLoaded', fn);
  }
}

whenReady(function() {
  console.log('📄 Page ready, waiting for diagrams...');
  
  // Give mermaid time to render, then initialize
  setTimeout(function() {
    initializeMermaidExtras();
  }, 1000);
});

function waitForSvgPanZoom(callback, attempts = 0) {
  if (typeof svgPanZoom !== 'undefined') {
    callback();
  } else if (attempts < 20) {
    setTimeout(() => waitForSvgPanZoom(callback, attempts + 1), 250);
  } else {
    console.error('❌ svg-pan-zoom failed to load after 5 seconds');
  }
}

function initializeMermaidExtras() {
  console.log('🔧 Starting Mermaid extras initialization...');
  
  // Find all mermaid diagrams
  const diagrams = document.querySelectorAll('.mermaid');
  console.log(`📊 Found ${diagrams.length} .mermaid elements`);
  
  if (diagrams.length === 0) {
    // Try again in a bit
    setTimeout(initializeMermaidExtras, 1000);
    return;
  }
  
  // Wait for svg-pan-zoom to be available
  waitForSvgPanZoom(function() {
    console.log('✅ svg-pan-zoom library loaded');
    
    diagrams.forEach((mermaidDiv, index) => {
      // Find SVG inside mermaid div
      const svg = mermaidDiv.querySelector('svg');
      
      if (!svg) {
        console.log(`⚠️  Diagram ${index + 1}: No SVG found inside .mermaid`);
        return;
      }
      
      // Skip if already processed
      if (mermaidDiv.dataset.panZoomInitialized === 'true') {
        console.log(`⏭️  Diagram ${index + 1}: Already initialized`);
        return;
      }
      
      console.log(`🎯 Diagram ${index + 1}: Initializing...`);
      
      try {
        // Ensure mermaid div is properly styled
        mermaidDiv.style.position = 'relative';
        mermaidDiv.style.overflow = 'visible';
        
        // Add fullscreen button
        if (!mermaidDiv.querySelector('.mermaid-fullscreen-btn')) {
          const fullscreenBtn = document.createElement('button');
          fullscreenBtn.innerHTML = '⛶';
          fullscreenBtn.className = 'mermaid-fullscreen-btn';
          fullscreenBtn.title = 'Toggle fullscreen (F)';
          fullscreenBtn.onclick = function() {
            toggleFullscreen(mermaidDiv);
          };
          mermaidDiv.appendChild(fullscreenBtn);
        }
        
        // Initialize pan-zoom on the SVG
        const panZoom = svgPanZoom(svg, {
          zoomEnabled: true,
          panEnabled: true,
          controlIconsEnabled: true,
          fit: true,
          center: true,
          minZoom: 0.1,
          maxZoom: 10,
          zoomScaleSensitivity: 0.3,
          dblClickZoomEnabled: true,
          mouseWheelZoomEnabled: true,
          preventMouseEventsDefault: true,
          contain: false,
          eventsListenerElement: svg
        });
        
        // Store instance
        svg._panZoom = panZoom;
        mermaidDiv.dataset.panZoomInitialized = 'true';
        
        console.log(`✅ Diagram ${index + 1}: Pan-zoom initialized successfully`);
        
        // Add keyboard controls
        svg.setAttribute('tabindex', '0');
        svg.addEventListener('keydown', function(e) {
          if (!panZoom) return;
          
          switch(e.key.toLowerCase()) {
            case 'r':
              e.preventDefault();
              panZoom.resetZoom();
              panZoom.center();
              break;
            case 'f':
              e.preventDefault();
              toggleFullscreen(mermaidDiv);
              break;
            case '+':
            case '=':
              e.preventDefault();
              panZoom.zoomIn();
              break;
            case '-':
              e.preventDefault();
              panZoom.zoomOut();
              break;
            case '0':
              e.preventDefault();
              panZoom.fit();
              panZoom.center();
              break;
          }
        });
        
        // Click on SVG to focus it
        svg.addEventListener('click', function() {
          svg.focus();
        });
        
      } catch (error) {
        console.error(`❌ Diagram ${index + 1}: Initialization failed:`, error);
      }
    });
    
    // Add help text
    console.log('💡 Pan-zoom controls: Drag to pan, scroll to zoom, R to reset, F for fullscreen');
  });
}

function toggleFullscreen(container) {
  const isFullscreen = container.classList.contains('mermaid-fullscreen');
  const svg = container.querySelector('svg');
  const panZoom = svg ? svg._panZoom : null;
  
  if (isFullscreen) {
    // Exit fullscreen
    container.classList.remove('mermaid-fullscreen');
    document.body.style.overflow = '';
  } else {
    // Enter fullscreen
    container.classList.add('mermaid-fullscreen');
    document.body.style.overflow = 'hidden';
  }
  
  // Refit diagram after transition
  if (panZoom) {
    setTimeout(function() {
      panZoom.resize();
      panZoom.fit();
      panZoom.center();
    }, 300);
  }
}

// Global escape key handler
document.addEventListener('keydown', function(e) {
  if (e.key === 'Escape') {
    const fullscreenElements = document.querySelectorAll('.mermaid-fullscreen');
    fullscreenElements.forEach(function(el) {
      el.classList.remove('mermaid-fullscreen');
      document.body.style.overflow = '';
      
      const svg = el.querySelector('svg');
      if (svg && svg._panZoom) {
        setTimeout(function() {
          svg._panZoom.resize();
          svg._panZoom.fit();
          svg._panZoom.center();
        }, 300);
      }
    });
  }
});

// Re-initialize when new content is added (for instant loading)
let reinitTimeout;
const observer = new MutationObserver(function(mutations) {
  let hasNewMermaid = false;
  
  mutations.forEach(function(mutation) {
    mutation.addedNodes.forEach(function(node) {
      if (node.nodeType === 1) { // Element node
        if (node.classList && node.classList.contains('mermaid')) {
          hasNewMermaid = true;
        } else if (node.querySelector && node.querySelector('.mermaid')) {
          hasNewMermaid = true;
        }
      }
    });
  });
  
  if (hasNewMermaid) {
    clearTimeout(reinitTimeout);
    reinitTimeout = setTimeout(function() {
      console.log('🔄 New mermaid content detected, reinitializing...');
      initializeMermaidExtras();
    }, 1000);
  }
});

// Start observing
setTimeout(function() {
  observer.observe(document.body, {
    childList: true,
    subtree: true
  });
}, 2000);
