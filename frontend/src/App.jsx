
import { useEffect, useRef, useState } from "react";
import {
  Html5Qrcode,
  Html5QrcodeScannerState,
  Html5QrcodeSupportedFormats,
} from "html5-qrcode";
import "./index.css";

const API_BASE_URL =
  import.meta.env.VITE_API_URL?.replace(/\/+$/, "") ||
  (import.meta.env.DEV ? `http://${window.location.hostname}:8000` : "");

if (window.location.protocol === "https:" && API_BASE_URL.startsWith("http:")) {
  throw new Error("VITE_API_URL must use HTTPS when the frontend uses HTTPS.");
}

function App() {
  // ============================================================
  // STATE
  // ============================================================

  const [barcode, setBarcode] = useState("");
  const [product, setProduct] = useState(null);

  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");

  const [summary, setSummary] = useState(null);

  const [loadingSummary, setLoadingSummary] = useState(false);
  const [loadingProduct, setLoadingProduct] = useState(false);
  const [loadingAnswer, setLoadingAnswer] = useState(false);

  const [error, setError] = useState("");
  const [scannerOpen, setScannerOpen] = useState(false);

  const scannerRef = useRef(null);
  const scannerStopRef = useRef(null);

  const stopScannerInstance = (scanner) => {
    if (!scanner) {
      return Promise.resolve();
    }

    if (scannerStopRef.current?.scanner === scanner) {
      return scannerStopRef.current.promise;
    }

    const promise = (async () => {
      try {
        const state = scanner.getState();
        if (
          state === Html5QrcodeScannerState.SCANNING ||
          state === Html5QrcodeScannerState.PAUSED
        ) {
          await scanner.stop();
        }
      } catch (error) {
        console.log("Scanner was already stopped.");
      }

      try {
        await scanner.clear();
      } catch (error) {
        console.log("Scanner was already cleared.");
      }
    })();

    scannerStopRef.current = { scanner, promise };
    promise.finally(() => {
      if (scannerStopRef.current?.scanner === scanner) {
        scannerStopRef.current = null;
      }
    });

    return promise;
  };

  // ============================================================
  // FIND PRODUCT
  // ============================================================

  const findProduct = async (code = barcode) => {
    const cleanCode = code.trim();

    if (!cleanCode) {
      setError("Please enter a barcode.");
      return;
    }

    const scanner = scannerRef.current;
    scannerRef.current = null;
    await stopScannerInstance(scanner);
    setScannerOpen(false);

    try {
      setLoadingProduct(true);
      setError("");
      setProduct(null);
      setAnswer("");
      setSummary(null);
      setQuestion("");

      // --------------------------------------------------------
      // Product API
      // --------------------------------------------------------

      const response = await fetch(
        `${API_BASE_URL}/product/barcode/${encodeURIComponent(cleanCode)}`
      );

      if (!response.ok) {
        throw new Error("Product not found.");
      }

      const data = await response.json();

      console.log("Product:", data);

      setBarcode(cleanCode);
      setProduct(data.product);

      // --------------------------------------------------------
      // Automatic AI Summary
      // --------------------------------------------------------

      if (data.product?.product_id) {
        try {
          setLoadingSummary(true);

          const summaryResponse = await fetch(
            `${API_BASE_URL}/product/${data.product.product_id}/summary`
          );

          if (!summaryResponse.ok) {
            throw new Error("Summary unavailable.");
          }

          const summaryData = await summaryResponse.json();

          console.log("AI Summary:", summaryData);

          setSummary(summaryData.summary);

        } catch (summaryError) {
          console.error(
            "Summary error:",
            summaryError
          );

          setSummary(null);

        } finally {
          setLoadingSummary(false);
        }
      }

    } catch (error) {
      console.error(
        "Product error:",
        error
      );

      setError(
        error.message ||
        "Unable to find product."
      );

    } finally {
      setLoadingProduct(false);
    }
  };

  // ============================================================
  // START SCANNER
  // ============================================================

  const startScanner = () => {
    setError("");
    setScannerOpen(true);
  };

  // ============================================================
  // STOP SCANNER
  // ============================================================

  const stopScanner = async () => {
    const scanner = scannerRef.current;
    scannerRef.current = null;

    await stopScannerInstance(scanner);
    setScannerOpen(false);
  };

  // ============================================================
  // BARCODE SCANNER
  // ============================================================

  useEffect(() => {
    if (!scannerOpen) {
      return;
    }

    const scanner = new Html5Qrcode("reader", {
      formatsToSupport: [
        Html5QrcodeSupportedFormats.EAN_13,
        Html5QrcodeSupportedFormats.EAN_8,
        Html5QrcodeSupportedFormats.UPC_A,
        Html5QrcodeSupportedFormats.UPC_E,
        Html5QrcodeSupportedFormats.CODE_128,
        Html5QrcodeSupportedFormats.CODE_39,
        Html5QrcodeSupportedFormats.ITF,
      ],
    });

    scannerRef.current = scanner;
    let active = true;

    scanner
      .start(
        {
          facingMode: "environment",
        },
        {
          fps: 10,
          qrbox: (viewfinderWidth, viewfinderHeight) => ({
            width: Math.floor(Math.min(viewfinderWidth * 0.82, 320)),
            height: Math.floor(Math.min(viewfinderHeight * 0.42, 150)),
          }),
          aspectRatio: 1.777778,
          videoConstraints: {
            facingMode: { ideal: "environment" },
          },
        },

        async (decodedText) => {
          if (!active || scannerRef.current !== scanner) {
            return;
          }

          console.log(
            "Barcode detected:",
            decodedText
          );

          setBarcode(decodedText);

          scannerRef.current = null;
          await stopScannerInstance(scanner);
          setScannerOpen(false);

          findProduct(decodedText);
        },

        () => {
          // Normal scanning errors are ignored.
        }
      )
      .then(() => {
        if (!active) {
          stopScannerInstance(scanner);
        }
      })
      .catch((error) => {
        if (!active) {
          return;
        }

        console.error(
          "Camera error:",
          error
        );

        setError(
          window.isSecureContext
            ? "Unable to access the camera. Check browser permission and ensure no other app is using it."
            : "Camera access requires HTTPS or localhost. Open the app using a secure URL on your phone."
        );

        setScannerOpen(false);
      });

    return () => {
      active = false;
      if (scannerRef.current === scanner) {
        scannerRef.current = null;
      }
      stopScannerInstance(scanner);
    };
  }, [scannerOpen]);

  // ============================================================
  // ASK DEALX-AI
  // ============================================================

  const askQuestion = async () => {
    if (!question.trim()) {
      setError("Please enter a question.");
      return;
    }

    if (!product) {
      setError(
        "Please find a product first."
      );
      return;
    }

    try {
      setLoadingAnswer(true);
      setError("");
      setAnswer("");

      let response;

      // ========================================================
      // EXTERNAL PRODUCT
      // ========================================================

      if (
        product.product_id &&
        product.product_id.startsWith("EXT-")
      ) {
        console.log(
          "Asking external product..."
        );

        response = await fetch(
          `${API_BASE_URL}/ask/barcode`,
          {
            method: "POST",

            headers: {
              "Content-Type": "application/json",
            },

            body: JSON.stringify({
              barcode: product.barcode,
              question: question.trim(),
            }),
          }
        );
      }

      // ========================================================
      // LOCAL PRODUCT
      // ========================================================

      else {
        console.log(
          "Asking local RAG product..."
        );

        response = await fetch(
          `${API_BASE_URL}/ask`,
          {
            method: "POST",

            headers: {
              "Content-Type": "application/json",
            },

            body: JSON.stringify({
              product_id: product.product_id,
              question: question.trim(),
            }),
          }
        );
      }

      // ========================================================
      // HANDLE ERROR
      // ========================================================

      if (!response.ok) {
        const errorData =
          await response.json().catch(
            () => null
          );

        throw new Error(
          errorData?.detail ||
          "Unable to get AI answer."
        );
      }

      // ========================================================
      // GET RESPONSE
      // ========================================================

      const data = await response.json();

      console.log(
        "AI Answer:",
        data
      );

      setAnswer(data.answer);

    } catch (error) {
      console.error(
        "AI error:",
        error
      );

      setError(
        error.message ||
        "Unable to get AI answer."
      );

    } finally {
      setLoadingAnswer(false);
    }
  };

  // ============================================================
  // RETURN UI
  // ============================================================

  return (
    <div className="app">

      {/* ======================================================
          HEADER
      ====================================================== */}

      <header className="header">

        <h1>
          DealX-AI
        </h1>

        <p>
          AI Shopping Assistant
        </p>

      </header>


      <main className="container">

        {/* ====================================================
            FIND PRODUCT
        ==================================================== */}

        <section className="search-card">

          <h2>
            Find a Product
          </h2>

          <p className="subtitle">
            Scan a barcode or enter it manually.
          </p>

          <div className="search-row">

            <input
              type="text"
              placeholder="Enter barcode..."
              value={barcode}
              onChange={(e) =>
                setBarcode(e.target.value)
              }
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  findProduct();
                }
              }}
            />

            <button
              className="find-button"
              onClick={() =>
                findProduct()
              }
              disabled={loadingProduct}
            >
              {loadingProduct
                ? "Searching..."
                : "Find Product"}
            </button>

          </div>


          <button
            className="scan-button"
            onClick={startScanner}
          >
            Scan Barcode
          </button>

        </section>


        {/* ====================================================
            SCANNER
        ==================================================== */}

        {scannerOpen && (

          <section className="scanner-card">

            <div id="reader"></div>

            <button
              className="stop-button"
              onClick={stopScanner}
            >
              Stop Scanner
            </button>

          </section>

        )}


        {/* ====================================================
            ERROR
        ==================================================== */}

        {error && (

          <div className="error-message">
            {error}
          </div>

        )}


        {/* ====================================================
            PRODUCT
        ==================================================== */}

        {product && (

          <section className="product-card">

            {/* Product Image */}

            {product.images?.length > 0 && (

              <div className="product-image">

                <img
                  src={product.images[0]}
                  alt={product.name}
                />

              </div>

            )}


            {/* Product Icon */}

            {!product.images?.length && (

              <div className="product-icon">
                PRODUCT
              </div>

            )}


            {/* Product Information */}

            <div className="product-info">

              <span className="product-label">
                PRODUCT FOUND
              </span>

              <h2>
                {product.name}
              </h2>


              {product.brand && (

                <p>
                  Brand:{" "}
                  <strong>
                    {product.brand}
                  </strong>
                </p>

              )}


              {product.model && (

                <p>
                  Model:{" "}
                  <strong>
                    {product.model}
                  </strong>
                </p>

              )}


              {product.product_id && (

                <p>
                  Product ID:{" "}
                  <strong>
                    {product.product_id}
                  </strong>
                </p>

              )}


              {product.barcode && (

                <p>
                  Barcode:{" "}
                  <strong>
                    {product.barcode}
                  </strong>
                </p>

              )}


              {product.category && (

                <p>
                  Category:{" "}
                  <strong>
                    {product.category}
                  </strong>
                </p>

              )}


              {product.price !== null &&
                product.price !== undefined && (

                  <p>
                    Price:{" "}
                    <strong>
                      {product.price}
                      {product.currency
                        ? ` ${product.currency}`
                        : ""}
                    </strong>
                  </p>

                )}


              {product.description && (

                <p className="product-description">
                  {product.description}
                </p>

              )}

            </div>

          </section>

        )}


        {/* ====================================================
            AI REVIEW / PRODUCT SUMMARY
        ==================================================== */}

        {product?.product_id && (

          <>

            {/* Loading Summary */}

            {loadingSummary && (

              <section className="summary-card">

                <div className="answer-header">

                  <span>
                    AI
                  </span>

                  <h2>
                    AI Product Summary
                  </h2>

                </div>


                <div className="summary-loading">

                  <div className="loading-spinner"></div>

                  <p>
                    Analyzing product information...
                  </p>

                </div>

              </section>

            )}


            {/* Actual Summary */}

            {!loadingSummary &&
              summary && (

                <section className="summary-card">

                  <div className="answer-header">

                    <span>
                      AI
                    </span>

                    <h2>
                      AI Product Summary
                    </h2>

                  </div>


                  <div className="summary-content">

                    {/* ==================================================
                        OVERALL
                    ================================================== */}

                    {summary.overall && (

                      <div className="overall-section">

                        <h3>
                          Overall
                        </h3>

                        <p>
                          {summary.overall}
                        </p>

                      </div>

                    )}


                    {/* ==================================================
                        PROS + CONS
                    ================================================== */}

                    <div className="pros-cons-grid">

                      {/* PROS */}

                      <div className="pros-box">

                        <h3>
                          Pros
                        </h3>


                        {summary.pros?.length > 0 ? (

                          <ul>

                            {summary.pros.map(
                              (pro, index) => (

                                <li key={index}>

                                  <span>
                                    ✓
                                  </span>

                                  <span>
                                    {pro}
                                  </span>

                                </li>

                              )
                            )}

                          </ul>

                        ) : (

                          <p>
                            No clear advantages
                            found.
                          </p>

                        )}

                      </div>


                      {/* CONS */}

                      <div className="cons-box">

                        <h3>
                          Cons
                        </h3>


                        {summary.cons?.length > 0 ? (

                          <ul>

                            {summary.cons.map(
                              (con, index) => (

                                <li key={index}>

                                  <span>
                                    ×
                                  </span>

                                  <span>
                                    {con}
                                  </span>

                                </li>

                              )
                            )}

                          </ul>

                        ) : (

                          <p>
                            No clear disadvantages
                            found.
                          </p>

                        )}

                      </div>

                    </div>


                    {/* ==================================================
                        VERDICT
                    ================================================== */}

                    {summary.verdict && (

                      <div className="verdict-box">

                        <h3>
                          Verdict
                        </h3>

                        <p>
                          {summary.verdict}
                        </p>

                      </div>

                    )}

                  </div>

                </section>

              )}

          </>

        )}


        {/* ====================================================
            ASK DEALX-AI
        ==================================================== */}

        {product?.product_id && (

          <section className="question-card">

            <h2>
              Ask DealX-AI
            </h2>

            <p className="subtitle">

              Ask anything about this product.

            </p>


            <textarea
              placeholder="Example: Is this phone good for photography?"
              value={question}
              onChange={(e) =>
                setQuestion(e.target.value)
              }
              onKeyDown={(e) => {

                if (
                  e.key === "Enter" &&
                  !e.shiftKey
                ) {

                  e.preventDefault();

                  askQuestion();

                }

              }}
            />


            <button
              className="ask-button"
              onClick={askQuestion}
              disabled={loadingAnswer}
            >

              {loadingAnswer
                ? "Thinking..."
                : "Ask DealX-AI"}

            </button>

          </section>

        )}


        {/* ====================================================
            AI ANSWER
        ==================================================== */}

        {answer && (

          <section className="answer-card">

            <div className="answer-header">

              <span>
                AI
              </span>

              <h2>
                DealX-AI Answer
              </h2>

            </div>


            <div className="answer-content">

              {answer
                .split("\n")
                .map((line, index) => (

                  <p key={index}>
                    {line}
                  </p>

                ))}

            </div>

          </section>

        )}


        {/* ====================================================
            FOOTER
        ==================================================== */}

        <footer>
          Powered by RAG + ChromaDB + Groq
        </footer>

      </main>

    </div>
  );
}

export default App;

