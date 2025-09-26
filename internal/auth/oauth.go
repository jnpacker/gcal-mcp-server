package auth

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"os"
	"path/filepath"
	"time"

	"golang.org/x/oauth2"
	"golang.org/x/oauth2/google"
	"google.golang.org/api/calendar/v3"
)

const (
	credentialsFile = "credentials.json"
	tokenFile       = "token.json"
)

func GetCalendarService() (*calendar.Service, error) {
	b, err := os.ReadFile(credentialsFile)
	if err != nil {
		return nil, fmt.Errorf("unable to read client secret file: %v", err)
	}

	config, err := google.ConfigFromJSON(b, calendar.CalendarScope)
	if err != nil {
		return nil, fmt.Errorf("unable to parse client secret file to config: %v", err)
	}

	client := getClient(config)

	srv, err := calendar.New(client)
	if err != nil {
		return nil, fmt.Errorf("unable to retrieve Calendar client: %v", err)
	}

	return srv, nil
}

func getClient(config *oauth2.Config) *http.Client {
	tokFile := tokenFile
	tok, err := tokenFromFile(tokFile)
	if err != nil {
		tok = getTokenFromWeb(config)
		saveToken(tokFile, tok)
	}
	return config.Client(context.Background(), tok)
}

func getTokenFromWeb(config *oauth2.Config) *oauth2.Token {
	// Set up a local server to handle the OAuth callback
	codeCh := make(chan string)
	errCh := make(chan error)

	// Create a temporary HTTP server to handle the callback
	server := &http.Server{Addr: ":8080"}

	http.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
		code := r.URL.Query().Get("code")
		if code == "" {
			errCh <- fmt.Errorf("no authorization code received")
			return
		}

		// Send success response to browser
		w.Header().Set("Content-Type", "text/html")
		fmt.Fprintf(w, `
			<html>
			<head><title>Authorization Successful</title></head>
			<body>
				<h1>Authorization Successful!</h1>
				<p>You can close this window and return to the terminal.</p>
			</body>
			</html>
		`)

		codeCh <- code
	})

	// Start the server in a goroutine
	go func() {
		if err := server.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			errCh <- fmt.Errorf("failed to start local server: %v", err)
		}
	}()

	// Update config to use localhost:8080 as redirect URI
	config.RedirectURL = "http://localhost:8080"

	authURL := config.AuthCodeURL("state-token", oauth2.AccessTypeOffline)
	fmt.Printf("Opening browser for authentication...\n")
	fmt.Printf("If the browser doesn't open automatically, go to: %v\n", authURL)

	// Try to open the browser automatically
	openBrowser(authURL)

	// Wait for either the code or an error
	var authCode string
	select {
	case authCode = <-codeCh:
		// Success - we got the code
	case err := <-errCh:
		log.Fatalf("OAuth error: %v", err)
	case <-time.After(5 * time.Minute):
		log.Fatalf("Timeout waiting for authorization")
	}

	// Shutdown the temporary server
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()
	server.Shutdown(ctx)

	// Exchange the code for a token
	tok, err := config.Exchange(context.TODO(), authCode)
	if err != nil {
		log.Fatalf("Unable to retrieve token from web: %v", err)
	}

	fmt.Printf("Authentication successful!\n")
	return tok
}

// openBrowser tries to open the URL in the default browser
func openBrowser(url string) {
	// This is a simple implementation - in a production system you might want
	// to use a more sophisticated approach or a library like "github.com/pkg/browser"
	fmt.Printf("Please visit the following URL to complete authentication:\n%s\n", url)
}

func tokenFromFile(file string) (*oauth2.Token, error) {
	f, err := os.Open(file)
	if err != nil {
		return nil, err
	}
	defer f.Close()
	tok := &oauth2.Token{}
	err = json.NewDecoder(f).Decode(tok)
	return tok, err
}

func saveToken(path string, token *oauth2.Token) {
	fmt.Printf("Saving credential file to: %s\n", path)
	f, err := os.OpenFile(path, os.O_RDWR|os.O_CREATE|os.O_TRUNC, 0600)
	if err != nil {
		log.Fatalf("Unable to cache oauth token: %v", err)
	}
	defer f.Close()
	json.NewEncoder(f).Encode(token)
}

func SetupCredentials() error {
	homeDir, err := os.UserHomeDir()
	if err != nil {
		return fmt.Errorf("unable to get user home directory: %v", err)
	}

	credPath := filepath.Join(homeDir, ".config", "gcal-mcp-server", credentialsFile)
	tokenPath := filepath.Join(homeDir, ".config", "gcal-mcp-server", tokenFile)

	if _, err := os.Stat(credPath); os.IsNotExist(err) {
		return fmt.Errorf("credentials.json not found at %s. Please download it from Google Cloud Console", credPath)
	}

	if _, err := os.Stat(tokenPath); os.IsNotExist(err) {
		fmt.Printf("Token file not found. Will need to authenticate via browser.\n")
	}

	return nil
}
