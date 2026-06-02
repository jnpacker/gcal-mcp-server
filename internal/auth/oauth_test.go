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

package auth

import (
	"os"
	"path/filepath"
	"testing"
	"time"

	"golang.org/x/oauth2"
)

// ----- isTokenValid -----

func TestIsTokenValid_NilToken(t *testing.T) {
	if isTokenValid(nil) {
		t.Error("nil token should not be valid")
	}
}

func TestIsTokenValid_EmptyAccessToken(t *testing.T) {
	tok := &oauth2.Token{Expiry: time.Now().Add(time.Hour)}
	if isTokenValid(tok) {
		t.Error("token with empty access token should not be valid")
	}
}

func TestIsTokenValid_Expired(t *testing.T) {
	tok := &oauth2.Token{
		AccessToken: "sometoken",
		Expiry:      time.Now().Add(-time.Hour), // expired
	}
	if isTokenValid(tok) {
		t.Error("expired token should not be valid")
	}
}

func TestIsTokenValid_ExpiresWithinBuffer(t *testing.T) {
	tok := &oauth2.Token{
		AccessToken: "sometoken",
		Expiry:      time.Now().Add(2 * time.Minute), // within 5-min buffer
	}
	if isTokenValid(tok) {
		t.Error("token expiring within buffer should not be valid")
	}
}

func TestIsTokenValid_Valid(t *testing.T) {
	tok := &oauth2.Token{
		AccessToken: "sometoken",
		Expiry:      time.Now().Add(time.Hour),
	}
	if !isTokenValid(tok) {
		t.Error("token with future expiry and non-empty access token should be valid")
	}
}

func TestIsTokenValid_NoExpiry(t *testing.T) {
	tok := &oauth2.Token{
		AccessToken: "sometoken",
		// zero Expiry means no expiry
	}
	if !isTokenValid(tok) {
		t.Error("token with no expiry and non-empty access token should be valid")
	}
}

// ----- findRepositoryRoot -----

func TestFindRepositoryRoot_FindsGoMod(t *testing.T) {
	// findRepositoryRoot walks from the source file's location — in a go module
	// it should always find the go.mod at the repo root.
	root, err := findRepositoryRoot()
	if err != nil {
		t.Fatalf("findRepositoryRoot() error: %v", err)
	}
	if _, err := os.Stat(filepath.Join(root, "go.mod")); err != nil {
		t.Errorf("expected go.mod to exist at %s: %v", root, err)
	}
}

// ----- getCredentialPaths -----

func TestGetCredentialPaths_ReturnsAbsolutePaths(t *testing.T) {
	credPath, tokenPath, err := getCredentialPaths()
	if err != nil {
		t.Fatalf("getCredentialPaths() error: %v", err)
	}
	if !filepath.IsAbs(credPath) {
		t.Errorf("credPath should be absolute, got %q", credPath)
	}
	if !filepath.IsAbs(tokenPath) {
		t.Errorf("tokenPath should be absolute, got %q", tokenPath)
	}
	if filepath.Base(credPath) != "credentials.json" {
		t.Errorf("expected credentials.json, got %q", filepath.Base(credPath))
	}
	if filepath.Base(tokenPath) != "token.json" {
		t.Errorf("expected token.json, got %q", filepath.Base(tokenPath))
	}
}

// ----- generateStateToken -----

func TestGenerateStateToken(t *testing.T) {
	tok1, err := generateStateToken()
	if err != nil {
		t.Fatalf("generateStateToken() error: %v", err)
	}
	if len(tok1) == 0 {
		t.Error("state token should not be empty")
	}

	tok2, err := generateStateToken()
	if err != nil {
		t.Fatalf("generateStateToken() second call error: %v", err)
	}
	if tok1 == tok2 {
		t.Error("consecutive state tokens should differ (random)")
	}
}
