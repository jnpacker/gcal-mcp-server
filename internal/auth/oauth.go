// Copyright 2024 Red Hat, Inc.
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.
//
// This code was developed with AI assistance.

package auth

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"os"
	"path/filepath"
	"runtime"
	"time"

	"golang.org/x/oauth2"
	"golang.org/x/oauth2/google"
	"google.golang.org/api/calendar/v3"
)

const (
	credentialsFile = "credentials.json"
	tokenFile       = "token.json"
)

// findRepositoryRoot walks up the directory tree to find the repository root
// by looking for go.mod file or .git directory
func findRepositoryRoot() (string, error) {
	// Start from the current executable's directory
	_, filename, _, ok := runtime.Caller(0)
	if !ok {
		return "", fmt.Errorf("unable to determine current file path")
	}

	dir := filepath.Dir(filename)

	// Walk up the directory tree
	for {
		// Check for go.mod file (Go module root)
		if _, err := os.Stat(filepath.Join(dir, "go.mod")); err == nil {
			return dir, nil
		}

		// Check for .git directory (Git repository root)
		if _, err := os.Stat(filepath.Join(dir, ".git")); err == nil {
			return dir, nil
		}

		// Move up one directory
		parent := filepath.Dir(dir)
		if parent == dir {
			// Reached filesystem root without finding repository markers
			break
		}
		dir = parent
	}

	return "", fmt.Errorf("repository root not found (no go.mod or .git found)")
}

// getCredentialPaths returns the full paths for credentials and token files
// First tries repository root, then falls back to current working directory
func getCredentialPaths() (string, string, error) {
	var credPath, tokenPath string

	// Try to find repository root
	if repoRoot, err := findRepositoryRoot(); err == nil {
		credPath = filepath.Join(repoRoot, credentialsFile)
		tokenPath = filepath.Join(repoRoot, tokenFile)
	} else {
		// Fallback to current working directory
		cwd, err := os.Getwd()
		if err != nil {
			return "", "", fmt.Errorf("unable to get current working directory: %v", err)
		}
		credPath = filepath.Join(cwd, credentialsFile)
		tokenPath = filepath.Join(cwd, tokenFile)
	}

	return credPath, tokenPath, nil
}

func GetCalendarService() (*calendar.Service, error) {
	credPath, tokenPath, err := getCredentialPaths()
	if err != nil {
		return nil, fmt.Errorf("unable to determine credential paths: %v", err)
	}

	b, err := os.ReadFile(credPath)
	if err != nil {
		return nil, fmt.Errorf("unable to read client secret file from %s: %v", credPath, err)
	}

	config, err := google.ConfigFromJSON(b, calendar.CalendarScope)
	if err != nil {
		return nil, fmt.Errorf("unable to parse client secret file to config: %v", err)
	}

	client := getClient(config, tokenPath)

	srv, err := calendar.New(client)
	if err != nil {
		return nil, fmt.Errorf("unable to retrieve Calendar client: %v", err)
	}

	return srv, nil
}

func getClient(config *oauth2.Config, tokenPath string) *http.Client {
	tok, err := tokenFromFile(tokenPath)
	if err != nil {
		tok = getTokenFromWeb(config)
		saveToken(tokenPath, tok)
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
	credPath, tokenPath, err := getCredentialPaths()
	if err != nil {
		return fmt.Errorf("unable to determine credential paths: %v", err)
	}

	if _, err := os.Stat(credPath); os.IsNotExist(err) {
		return fmt.Errorf("credentials.json not found at %s. Please download it from Google Cloud Console and place it in the repository root", credPath)
	}

	if _, err := os.Stat(tokenPath); os.IsNotExist(err) {
		fmt.Printf("Token file not found at %s. Will need to authenticate via browser.\n", tokenPath)
	} else {
		fmt.Printf("Found existing token at %s\n", tokenPath)
	}

	return nil
}
